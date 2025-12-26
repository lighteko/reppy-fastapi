"""
Pipeline orchestrator - routes requests to appropriate pipelines.

Main entry point for processing worker requests.
"""

import logging
import time
from typing import Any, Dict, Optional

from ..contracts import (
    WorkerRequest,
    ResultEvent,
    ResultStatus,
    IntentRoutingOutput,
    FallbackIntentRouting,
    Intent,
)
from ..context import (
    ContextAggregator,
    VMInternalAPIAdapter,
    QdrantAdapter,
)
from ..emit import (
    TokenStreamPort,
    ResultQueuePort,
    OCIStreamingAdapter,
    OCIQueueAdapter,
)
from ..llm import GeminiClient, PromptLoader, get_gemini_client, get_prompt_loader
from .chat_pipeline import ChatPipeline
from .generate_pipeline import GeneratePipeline
from .update_pipeline import UpdatePipeline

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Main orchestrator for pipeline execution.
    
    Handles:
    1. Idempotency claims
    2. Intent routing
    3. Pipeline dispatch
    4. Result publishing
    """

    def __init__(
        self,
        vm_adapter: Optional[VMInternalAPIAdapter] = None,
        qdrant_adapter: Optional[QdrantAdapter] = None,
        token_stream: Optional[TokenStreamPort] = None,
        result_queue: Optional[ResultQueuePort] = None,
        gemini_client: Optional[GeminiClient] = None,
        prompt_loader: Optional[PromptLoader] = None,
    ):
        """
        Initialize orchestrator with adapters.
        
        Args:
            vm_adapter: VM internal API adapter.
            qdrant_adapter: Qdrant adapter.
            token_stream: Token stream port.
            result_queue: Result queue port.
            gemini_client: Gemini LLM client.
            prompt_loader: Prompt loader.
        """
        # Initialize adapters
        self._vm_adapter = vm_adapter or VMInternalAPIAdapter()
        self._qdrant_adapter = qdrant_adapter or QdrantAdapter()
        self._token_stream = token_stream or OCIStreamingAdapter()
        self._result_queue = result_queue or OCIQueueAdapter()
        self._gemini = gemini_client or get_gemini_client()
        self._prompt_loader = prompt_loader or get_prompt_loader()
        
        # Initialize context aggregator
        self._context_aggregator = ContextAggregator(
            context_port=self._vm_adapter,
            vector_port=self._qdrant_adapter,
        )
        
        # Initialize pipelines
        self._chat_pipeline = ChatPipeline(
            gemini_client=self._gemini,
            prompt_loader=self._prompt_loader,
            context_aggregator=self._context_aggregator,
            token_stream=self._token_stream,
            result_queue=self._result_queue,
        )
        self._generate_pipeline = GeneratePipeline(
            gemini_client=self._gemini,
            prompt_loader=self._prompt_loader,
            context_aggregator=self._context_aggregator,
            token_stream=self._token_stream,
            result_queue=self._result_queue,
        )
        self._update_pipeline = UpdatePipeline(
            gemini_client=self._gemini,
            prompt_loader=self._prompt_loader,
            context_aggregator=self._context_aggregator,
            token_stream=self._token_stream,
            result_queue=self._result_queue,
        )

    async def process(self, request: WorkerRequest) -> ResultEvent:
        """
        Process a single worker request.
        
        Args:
            request: The worker request.
            
        Returns:
            Result event.
        """
        request_id = request.requestId
        overall_start = time.perf_counter()
        
        logger.info(f"[{request_id}] Processing request for user {request.userId}")
        
        try:
            # Step 1: Idempotency claim
            claimed = await self._vm_adapter.claim(request_id)
            if not claimed:
                logger.info(f"[{request_id}] Request already claimed, skipping")
                return ResultEvent(
                    requestId=request_id,
                    status=ResultStatus.SUCCEEDED,
                    final={"skipped": True, "reason": "already_claimed"},
                )
            
            # Step 2: Fetch user profile
            user_profile = await self._vm_adapter.get_user_profile(request.userId)
            
            # Step 3: Route intent
            routing_start = time.perf_counter()
            intent_result = await self._route_intent(request)
            routing_elapsed = (time.perf_counter() - routing_start) * 1000
            
            logger.info(
                f"[{request_id}] Intent routing completed in {routing_elapsed:.2f}ms: "
                f"intent={intent_result.intent.value}, confidence={intent_result.confidence}"
            )
            
            # Check for clarification at routing level
            if intent_result.needs_clarification:
                result = ResultEvent(
                    requestId=request_id,
                    status=ResultStatus.CLARIFY,
                    final={"reply": intent_result.clarification_question},
                    meta={
                        "intent": intent_result.intent.value,
                        "action": "INTENT_ROUTING",
                        "confidence": intent_result.confidence,
                    },
                )
                await self._result_queue.publish(result)
                return result
            
            # Step 4: Dispatch to appropriate pipeline
            result = await self._dispatch(intent_result.intent, request, user_profile)
            
            # Step 5: Publish result
            await self._result_queue.publish(result)
            
            overall_elapsed = (time.perf_counter() - overall_start) * 1000
            logger.info(
                f"[{request_id}] Request completed in {overall_elapsed:.2f}ms: "
                f"status={result.status.value}"
            )
            
            return result
            
        except Exception as e:
            overall_elapsed = (time.perf_counter() - overall_start) * 1000
            logger.error(
                f"[{request_id}] Request failed in {overall_elapsed:.2f}ms: {e}",
                exc_info=True,
            )
            
            result = ResultEvent(
                requestId=request_id,
                status=ResultStatus.FAILED,
                error={"code": "INTERNAL_ERROR", "message": str(e)},
            )
            
            try:
                await self._result_queue.publish(result)
            except Exception as pub_error:
                logger.error(f"[{request_id}] Failed to publish error result: {pub_error}")
            
            return result

    async def _route_intent(self, request: WorkerRequest) -> IntentRoutingOutput:
        """Route the request to determine intent."""
        # Try action_routing first (as specified in requirements), fall back to intent_routing
        try:
            template = self._prompt_loader.load("action_routing")
        except FileNotFoundError:
            template = self._prompt_loader.load("intent_routing")
        
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]
        
        variables = {
            "conversation_history": conversation_history,
        }
        
        system_prompt, user_prompt = self._prompt_loader.render(template, variables)
        
        try:
            result = await self._gemini.invoke_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=IntentRoutingOutput,
                use_router_model=True,
                request_id=request.requestId,
            )
            return result
        except Exception as e:
            logger.error(f"[{request.requestId}] Intent routing failed: {e}", exc_info=True)
            return FallbackIntentRouting()

    async def _dispatch(
        self,
        intent: Intent,
        request: WorkerRequest,
        user_profile: Dict[str, Any],
    ) -> ResultEvent:
        """Dispatch to the appropriate pipeline based on intent."""
        if intent == Intent.CHAT_RESPONSE:
            return await self._chat_pipeline.execute(request, user_profile)
        elif intent == Intent.GENERATE_ROUTINE:
            return await self._generate_pipeline.execute(request, user_profile)
        elif intent == Intent.UPDATE_ROUTINE:
            return await self._update_pipeline.execute(request, user_profile)
        else:
            logger.warning(f"[{request.requestId}] Unknown intent: {intent}")
            return await self._chat_pipeline.execute(request, user_profile)

    async def close(self) -> None:
        """Close all adapters and cleanup resources."""
        await self._vm_adapter.close()
        await self._qdrant_adapter.close()
        if isinstance(self._token_stream, OCIStreamingAdapter):
            await self._token_stream.close()
        if isinstance(self._result_queue, OCIQueueAdapter):
            await self._result_queue.close()

    async def __aenter__(self) -> "PipelineOrchestrator":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()

