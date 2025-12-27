"""Pipeline orchestrator - coordinates the full request processing flow."""

import logging
from typing import Any

from src.config import Settings
from src.context.adapters.aggregator import DefaultContextAggregator
from src.context.adapters.vm_client import VMApiClient
from src.contracts.messages import (
    RequestPayload,
    ResultEvent,
    ResultMeta,
    ResultStatus,
    UsageInfo,
)
from src.contracts.schemas import IntentType
from src.emit.ports import ResultPublisher, TokenStreamer
from src.llm.gemini import GeminiClient
from src.pipelines.chat_pipeline import ChatPipeline
from src.pipelines.generate_pipeline import GeneratePipeline
from src.pipelines.router import IntentRouter
from src.pipelines.update_pipeline import UpdatePipeline
from src.utils.logging import latency_log, set_request_id
from src.utils.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates the full request processing pipeline.
    
    1. Claims idempotency
    2. Routes intent
    3. Executes appropriate pipeline
    4. Publishes result
    """

    def __init__(
        self,
        settings: Settings,
        vm_client: VMApiClient,
        context_aggregator: DefaultContextAggregator,
        token_streamer: TokenStreamer,
        result_publisher: ResultPublisher,
        prompt_loader: PromptLoader | None = None,
        llm_client: GeminiClient | None = None,
    ) -> None:
        """
        Initialize orchestrator.
        
        Args:
            settings: Application settings.
            vm_client: VM API client for idempotency and user data.
            context_aggregator: Context aggregation service.
            token_streamer: Token streaming service.
            result_publisher: Result publishing service.
            prompt_loader: Optional pre-configured prompt loader.
            llm_client: Optional pre-configured LLM client.
        """
        self._settings = settings
        self._vm_client = vm_client
        self._context = context_aggregator
        self._streamer = token_streamer
        self._publisher = result_publisher
        self._prompt_loader = prompt_loader or PromptLoader(settings.prompts_dir)
        self._llm = llm_client or GeminiClient(settings)

        # Initialize pipelines
        self._router = IntentRouter(settings, self._prompt_loader, self._llm)
        self._chat_pipeline = ChatPipeline(
            settings, self._prompt_loader, self._llm, context_aggregator, token_streamer
        )
        self._generate_pipeline = GeneratePipeline(
            settings, self._prompt_loader, self._llm
        )
        self._update_pipeline = UpdatePipeline(
            settings, self._prompt_loader, self._llm
        )

    async def process(self, payload: RequestPayload) -> None:
        """
        Process a single request through the pipeline.
        
        Args:
            payload: Request payload from queue.
        """
        request_id = payload.request_id
        set_request_id(request_id)

        logger.info(f"Processing request for user {payload.user_id}")

        try:
            # Step 1: Claim idempotency
            with latency_log(logger, "Idempotency claim"):
                claimed = await self._vm_client.claim_idempotency(request_id)

            if not claimed:
                logger.info(f"Request {request_id} already claimed, skipping")
                return

            # Step 2: Fetch user profile
            with latency_log(logger, "Fetch user profile"):
                user_profile = await self._vm_client.get_user_profile(payload.user_id)

            # Step 3: Route intent
            conversation_history = [
                {"role": msg.role, "content": msg.content}
                for msg in payload.conversation_history
            ]

            routing = await self._router.route(conversation_history)

            # Step 4: Handle based on intent
            if routing.needs_clarification:
                await self._publish_clarification(
                    request_id=request_id,
                    question=routing.clarification_question,
                    routing=routing,
                )
                return

            if routing.intent == IntentType.CHAT_RESPONSE:
                await self._handle_chat(payload, user_profile, routing)

            elif routing.intent == IntentType.GENERATE_ROUTINE:
                await self._handle_generate(payload, user_profile, routing)

            elif routing.intent == IntentType.UPDATE_ROUTINE:
                await self._handle_update(payload, user_profile, routing)

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            await self._publish_error(request_id, str(e))

    async def _handle_chat(
        self,
        payload: RequestPayload,
        user_profile: dict[str, Any],
        routing: Any,
    ) -> None:
        """Handle CHAT_RESPONSE intent."""
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in payload.conversation_history
        ]

        result = await self._chat_pipeline.execute(
            request_id=payload.request_id,
            user_id=payload.user_id,
            user_profile=user_profile,
            conversation_history=conversation_history,
            routing=routing,
            stream=payload.stream,
        )

        await self._publisher.publish(
            ResultEvent(
                request_id=payload.request_id,
                status=ResultStatus.SUCCEEDED,
                final={"reply": result.reply, "suggested_questions": result.suggested_questions},
                meta=ResultMeta(
                    intent=IntentType.CHAT_RESPONSE.value,
                    action="chat_response",
                    confidence=routing.confidence,
                ),
            )
        )

    async def _handle_generate(
        self,
        payload: RequestPayload,
        user_profile: dict[str, Any],
        routing: Any,
    ) -> None:
        """Handle GENERATE_ROUTINE intent."""
        try:
            # Extract job context from metadata
            job_context = payload.metadata.get("job_context", {})
            available_context = payload.metadata.get("available_context", {"exercises": [], "set_types": []})

            # Optionally fetch current routines
            current_routines: list[dict[str, Any]] = []
            if "active_routines" in routing.required_context:
                routines_data = await self._vm_client.get_active_routines(payload.user_id)
                current_routines = routines_data.get("routines", [])

            result = await self._generate_pipeline.execute(
                user_profile=user_profile,
                job_context=job_context,
                available_context=available_context,
                current_routines=current_routines,
            )

            await self._publisher.publish(
                ResultEvent(
                    request_id=payload.request_id,
                    status=ResultStatus.SUCCEEDED,
                    final={"routines": [r.model_dump() for r in result.routines]},
                    meta=ResultMeta(
                        intent=IntentType.GENERATE_ROUTINE.value,
                        action="generate_program",
                        confidence=routing.confidence,
                    ),
                )
            )

        except ValueError as e:
            await self._publish_error(payload.request_id, str(e))

    async def _handle_update(
        self,
        payload: RequestPayload,
        user_profile: dict[str, Any],
        routing: Any,
    ) -> None:
        """Handle UPDATE_ROUTINE intent."""
        try:
            # Get the routine to update from metadata or fetch from API
            routine_to_update = payload.metadata.get("routine_to_update")
            if not routine_to_update:
                routines_data = await self._vm_client.get_active_routines(payload.user_id)
                routines = routines_data.get("routines", [])
                if routines:
                    routine_to_update = routines[0]  # Use first routine as default
                else:
                    await self._publish_error(
                        payload.request_id,
                        "No active routine found to update",
                    )
                    return

            # Extract update request from conversation
            latest_message = ""
            if payload.conversation_history:
                latest_message = payload.conversation_history[-1].content

            user_update_request = {
                "routine_name": routine_to_update.get("routine_name", ""),
                "additional_info": latest_message,
            }

            available_context = payload.metadata.get(
                "available_context",
                {"exercises": [], "set_types": []},
            )

            result = await self._update_pipeline.execute(
                user_profile=user_profile,
                user_update_request=user_update_request,
                available_context=available_context,
                routine_to_update=routine_to_update,
            )

            await self._publisher.publish(
                ResultEvent(
                    request_id=payload.request_id,
                    status=ResultStatus.SUCCEEDED,
                    final={"routine": result.model_dump()},
                    meta=ResultMeta(
                        intent=IntentType.UPDATE_ROUTINE.value,
                        action="update_routine",
                        confidence=routing.confidence,
                    ),
                )
            )

        except ValueError as e:
            await self._publish_error(payload.request_id, str(e))

    async def _publish_clarification(
        self,
        request_id: str,
        question: str,
        routing: Any,
    ) -> None:
        """Publish a clarification response."""
        await self._publisher.publish(
            ResultEvent(
                request_id=request_id,
                status=ResultStatus.CLARIFY,
                final={"reply": question},
                meta=ResultMeta(
                    intent=routing.intent.value if hasattr(routing, "intent") else "",
                    action="clarify",
                    confidence=routing.confidence if hasattr(routing, "confidence") else 0.0,
                ),
            )
        )

    async def _publish_error(self, request_id: str, message: str) -> None:
        """Publish an error result."""
        await self._publisher.publish(
            ResultEvent(
                request_id=request_id,
                status=ResultStatus.FAILED,
                error={"code": "PIPELINE_ERROR", "message": message},
                meta=ResultMeta(),
            )
        )

