"""
Chat response pipeline.

Flow:
1. Plan with chat_planner (router model)
2. Aggregate context based on required_context
3. Generate response with chat_response (main model, optionally streaming)
"""

import json
import logging
import time
from typing import Any, Dict

from ..contracts import (
    WorkerRequest,
    ResultEvent,
    TokenStreamEvent,
    ChatPlannerOutput,
    ChatResponseOutput,
    FallbackChatPlanner,
    PlannerAction,
)
from .base import BasePipeline

logger = logging.getLogger(__name__)


class ChatPipeline(BasePipeline):
    """
    Pipeline for CHAT_RESPONSE intent.
    
    Uses chat_planner to decide action and context,
    then chat_response to generate the final reply.
    """

    async def execute(
        self,
        request: WorkerRequest,
        user_profile: Dict[str, Any],
    ) -> ResultEvent:
        """
        Execute the chat pipeline.
        
        Args:
            request: Worker request.
            user_profile: User profile data.
            
        Returns:
            Result event.
        """
        request_id = request.requestId
        
        # Step 1: Planning
        logger.info(f"[{request_id}] Starting chat planning")
        plan_start = time.perf_counter()
        
        plan = await self._run_planner(request, user_profile)
        
        plan_elapsed = (time.perf_counter() - plan_start) * 1000
        logger.info(
            f"[{request_id}] Chat planning completed in {plan_elapsed:.2f}ms: "
            f"action={plan.action.value}, confidence={plan.confidence}"
        )
        
        # Check for clarification
        if plan.needs_clarification or plan.action == PlannerAction.ASK_CLARIFY:
            return self._create_clarify_result(
                request_id=request_id,
                reply=plan.clarification_question,
                meta={
                    "intent": "CHAT_RESPONSE",
                    "action": plan.action.value,
                    "confidence": plan.confidence,
                },
            )
        
        # Check for handoff
        if plan.action == PlannerAction.HANDOFF_INTENT_ROUTER:
            # Return clarification asking if they want new or update
            return self._create_clarify_result(
                request_id=request_id,
                reply="새로운 루틴을 만들어 드릴까요, 아니면 기존 루틴을 수정할까요?",
                meta={
                    "intent": "CHAT_RESPONSE",
                    "action": plan.action.value,
                    "confidence": plan.confidence,
                },
            )
        
        # Step 2: Context aggregation
        logger.info(f"[{request_id}] Aggregating context: {plan.required_context}")
        ctx_start = time.perf_counter()
        
        latest_message = self._get_latest_user_message(request.conversation_history)
        context = await self._context_aggregator.aggregate(
            user_id=request.userId,
            required_context=plan.required_context,
            args=plan.args,
            fallback_query=latest_message,
            request_id=request_id,
        )
        
        ctx_elapsed = (time.perf_counter() - ctx_start) * 1000
        logger.info(f"[{request_id}] Context aggregation completed in {ctx_elapsed:.2f}ms")
        
        # Step 3: Generate response
        logger.info(f"[{request_id}] Generating response (stream={request.stream and plan.should_stream})")
        resp_start = time.perf_counter()
        
        if request.stream and plan.should_stream:
            response = await self._run_responder_streaming(
                request=request,
                user_profile=user_profile,
                plan=plan,
                context=context,
            )
        else:
            response = await self._run_responder(
                request=request,
                user_profile=user_profile,
                plan=plan,
                context=context,
            )
        
        resp_elapsed = (time.perf_counter() - resp_start) * 1000
        logger.info(f"[{request_id}] Response generation completed in {resp_elapsed:.2f}ms")
        
        # Build final result
        final = {"reply": response.reply}
        if response.suggested_questions:
            final["suggested_questions"] = response.suggested_questions
        
        return self._create_success_result(
            request_id=request_id,
            final=final,
            meta={
                "intent": "CHAT_RESPONSE",
                "action": plan.action.value,
                "confidence": plan.confidence,
            },
        )

    async def _run_planner(
        self,
        request: WorkerRequest,
        user_profile: Dict[str, Any],
    ) -> ChatPlannerOutput:
        """Run the chat planner to decide action and context."""
        template = self._prompt_loader.load("chat_planner")
        
        variables = {
            "user_profile": user_profile,
            "conversation_history": self._conversation_to_list(request.conversation_history),
        }
        
        system_prompt, user_prompt = self._prompt_loader.render(template, variables)
        
        try:
            result = await self._gemini.invoke_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=ChatPlannerOutput,
                use_router_model=True,
                request_id=request.requestId,
            )
            return result
        except Exception as e:
            logger.error(f"[{request.requestId}] Planner failed: {e}", exc_info=True)
            # Return fallback
            return FallbackChatPlanner()

    async def _run_responder(
        self,
        request: WorkerRequest,
        user_profile: Dict[str, Any],
        plan: ChatPlannerOutput,
        context: Dict[str, Any],
    ) -> ChatResponseOutput:
        """Run the chat responder without streaming."""
        template = self._prompt_loader.load("chat_response")
        
        variables = {
            "user_profile": user_profile,
            "conversation_history": self._conversation_to_list(request.conversation_history),
            "plan": plan.model_dump(),
            "context": context,
        }
        
        system_prompt, user_prompt = self._prompt_loader.render(template, variables)
        
        try:
            result = await self._gemini.invoke_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=ChatResponseOutput,
                use_router_model=False,
                request_id=request.requestId,
            )
            return result
        except Exception as e:
            logger.error(f"[{request.requestId}] Responder failed: {e}", exc_info=True)
            return ChatResponseOutput(
                reply="죄송합니다. 응답을 생성하는 데 문제가 발생했어요. 다시 시도해 주세요."
            )

    async def _run_responder_streaming(
        self,
        request: WorkerRequest,
        user_profile: Dict[str, Any],
        plan: ChatPlannerOutput,
        context: Dict[str, Any],
    ) -> ChatResponseOutput:
        """Run the chat responder with streaming."""
        template = self._prompt_loader.load("chat_response")
        
        variables = {
            "user_profile": user_profile,
            "conversation_history": self._conversation_to_list(request.conversation_history),
            "plan": plan.model_dump(),
            "context": context,
        }
        
        system_prompt, user_prompt = self._prompt_loader.render(template, variables)
        
        # Stream tokens and collect full response
        full_response = ""
        seq = 0
        
        try:
            async for chunk in self._gemini.stream(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                use_router_model=False,
                request_id=request.requestId,
            ):
                full_response += chunk
                seq += 1
                
                # Publish token event
                event = TokenStreamEvent(
                    requestId=request.requestId,
                    seq=seq,
                    delta=chunk,
                    ts=int(time.time() * 1000),
                )
                await self._token_stream.publish(event)
            
            # Flush remaining tokens
            await self._token_stream.flush()
            
            # Parse the full response as JSON
            from ..llm import StructuredOutputParser
            
            parsed, error = StructuredOutputParser.parse(
                full_response,
                ChatResponseOutput,
                request.requestId,
            )
            
            if parsed:
                return parsed
            else:
                # If parsing fails, use the raw response as reply
                # Try to extract just the reply text
                return ChatResponseOutput(reply=full_response.strip())
                
        except Exception as e:
            logger.error(f"[{request.requestId}] Streaming responder failed: {e}", exc_info=True)
            return ChatResponseOutput(
                reply="죄송합니다. 응답을 생성하는 데 문제가 발생했어요. 다시 시도해 주세요."
            )

