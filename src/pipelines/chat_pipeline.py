"""Chat response pipeline with planning and context aggregation."""

import logging
from typing import Any

from src.config import Settings
from src.context.adapters.aggregator import DefaultContextAggregator
from src.contracts.messages import TokenStreamEvent
from src.contracts.schemas import (
    ChatPlannerAction,
    ChatPlannerOutput,
    ChatResponseOutput,
    IntentRoutingOutput,
)
from src.emit.ports import TokenStreamer
from src.llm.gemini import GeminiClient, ModelType
from src.utils.logging import latency_log
from src.utils.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class ChatPipeline:
    """
    Chat response pipeline.
    
    1. Plans what context to fetch (using planner)
    2. Aggregates required context
    3. Generates response (optionally streaming)
    """

    def __init__(
        self,
        settings: Settings,
        prompt_loader: PromptLoader,
        llm_client: GeminiClient,
        context_aggregator: DefaultContextAggregator,
        token_streamer: TokenStreamer | None = None,
    ) -> None:
        """
        Initialize chat pipeline.
        
        Args:
            settings: Application settings.
            prompt_loader: Prompt template loader.
            llm_client: Gemini LLM client.
            context_aggregator: Context aggregation service.
            token_streamer: Optional token streamer for streaming responses.
        """
        self._settings = settings
        self._prompt_loader = prompt_loader
        self._llm = llm_client
        self._context = context_aggregator
        self._streamer = token_streamer

    async def execute(
        self,
        request_id: str,
        user_id: str,
        user_profile: dict[str, Any],
        conversation_history: list[dict[str, Any]],
        routing: IntentRoutingOutput,
        stream: bool = True,
    ) -> ChatResponseOutput:
        """
        Execute chat response pipeline.
        
        Args:
            request_id: Request identifier.
            user_id: User identifier.
            user_profile: User profile data.
            conversation_history: Conversation history.
            routing: Intent routing output.
            stream: Whether to stream response.
            
        Returns:
            Chat response output.
        """
        # Step 1: Plan
        with latency_log(logger, "Chat planning"):
            plan = await self._plan(user_profile, conversation_history)

        logger.info(
            f"Chat plan: action={plan.action.value} "
            f"should_stream={plan.should_stream} "
            f"required_context={plan.required_context}"
        )

        # Handle immediate clarification
        if plan.needs_clarification or plan.action == ChatPlannerAction.ASK_CLARIFY:
            return ChatResponseOutput(
                reply=plan.clarification_question or "무엇을 도와드릴까요?",
                suggested_questions=[],
            )

        # Handle handoff (shouldn't happen normally)
        if plan.action == ChatPlannerAction.HANDOFF_INTENT_ROUTER:
            return ChatResponseOutput(
                reply="새 루틴을 만들고 싶으신 건가요, 아니면 기존 루틴을 수정하고 싶으신 건가요?",
                suggested_questions=[],
            )

        # Step 2: Aggregate context
        # Merge required_context from routing and planning
        all_required_context = list(set(routing.required_context + plan.required_context))
        query = plan.args.get("query") if plan.args else None

        with latency_log(logger, "Context aggregation"):
            context = await self._context.aggregate(
                user_id=user_id,
                required_context=all_required_context,
                query=query,
            )

        # Step 3: Generate response
        should_stream = stream and plan.should_stream and self._streamer is not None

        if should_stream:
            return await self._generate_streaming(
                request_id=request_id,
                user_profile=user_profile,
                conversation_history=conversation_history,
                plan=plan,
                context=context,
            )
        else:
            return await self._generate_direct(
                user_profile=user_profile,
                conversation_history=conversation_history,
                plan=plan,
                context=context,
            )

    async def _plan(
        self,
        user_profile: dict[str, Any],
        conversation_history: list[dict[str, Any]],
    ) -> ChatPlannerOutput:
        """Run chat planner."""
        try:
            prompt = self._prompt_loader.load("chat_planner")

            return await self._llm.invoke_structured(
                prompt=prompt,
                output_model=ChatPlannerOutput,
                model_type=ModelType.ROUTER,
                user_profile=user_profile,
                conversation_history=conversation_history,
            )
        except Exception as e:
            logger.error(f"Chat planning failed: {e}", exc_info=True)
            # Fallback to direct answer
            return ChatPlannerOutput(
                action=ChatPlannerAction.ASK_CLARIFY,
                confidence=0.5,
                required_context=[],
                args={},
                should_stream=False,
                needs_clarification=True,
                clarification_question="죄송해요, 요청을 처리하는 데 문제가 생겼어요. 다시 말씀해 주시겠어요?",
                notes="Planning failed, asking for clarification",
            )

    async def _generate_direct(
        self,
        user_profile: dict[str, Any],
        conversation_history: list[dict[str, Any]],
        plan: ChatPlannerOutput,
        context: dict[str, Any],
    ) -> ChatResponseOutput:
        """Generate response without streaming."""
        with latency_log(logger, "Chat response generation"):
            try:
                prompt = self._prompt_loader.load("chat_response")

                return await self._llm.invoke_structured(
                    prompt=prompt,
                    output_model=ChatResponseOutput,
                    model_type=ModelType.MAIN,
                    user_profile=user_profile,
                    conversation_history=conversation_history,
                    plan=plan.model_dump(),
                    context=context,
                )
            except Exception as e:
                logger.error(f"Response generation failed: {e}", exc_info=True)
                return ChatResponseOutput(
                    reply="죄송해요, 응답을 생성하는 데 문제가 생겼어요. 잠시 후 다시 시도해 주세요.",
                    suggested_questions=[],
                )

    async def _generate_streaming(
        self,
        request_id: str,
        user_profile: dict[str, Any],
        conversation_history: list[dict[str, Any]],
        plan: ChatPlannerOutput,
        context: dict[str, Any],
    ) -> ChatResponseOutput:
        """Generate response with streaming."""
        with latency_log(logger, "Chat response generation (streaming)"):
            try:
                prompt = self._prompt_loader.load("chat_response")

                token_iter, collector = await self._llm.invoke_streaming_structured(
                    prompt=prompt,
                    output_model=ChatResponseOutput,
                    model_type=ModelType.MAIN,
                    user_profile=user_profile,
                    conversation_history=conversation_history,
                    plan=plan.model_dump(),
                    context=context,
                )

                # Stream tokens
                seq = 0
                async for token in token_iter:
                    if self._streamer:
                        seq += 1
                        event = TokenStreamEvent(
                            request_id=request_id,
                            seq=seq,
                            delta=token,
                        )
                        await self._streamer.publish(event)

                # Flush remaining tokens
                if self._streamer:
                    await self._streamer.flush(request_id)

                # Parse final result
                return collector.parse()

            except Exception as e:
                logger.error(f"Streaming response failed: {e}", exc_info=True)
                return ChatResponseOutput(
                    reply="죄송해요, 응답을 생성하는 데 문제가 생겼어요. 잠시 후 다시 시도해 주세요.",
                    suggested_questions=[],
                )

