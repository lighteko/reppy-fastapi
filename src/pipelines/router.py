"""Intent routing pipeline."""

import logging
from typing import Any

from src.config import Settings
from src.contracts.schemas import IntentRoutingOutput, IntentType
from src.llm.gemini import GeminiClient, ModelType
from src.utils.logging import latency_log
from src.utils.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class IntentRouter:
    """
    Routes user messages to appropriate handlers based on intent.
    
    Uses the router model (fast, cheap) for classification.
    """

    def __init__(
        self,
        settings: Settings,
        prompt_loader: PromptLoader,
        llm_client: GeminiClient,
    ) -> None:
        """
        Initialize intent router.
        
        Args:
            settings: Application settings.
            prompt_loader: Prompt template loader.
            llm_client: Gemini LLM client.
        """
        self._settings = settings
        self._prompt_loader = prompt_loader
        self._llm = llm_client

    async def route(
        self,
        conversation_history: list[dict[str, Any]],
    ) -> IntentRoutingOutput:
        """
        Route user message to appropriate handler.
        
        Args:
            conversation_history: Recent conversation history.
            
        Returns:
            Routing output with intent and context requirements.
        """
        with latency_log(logger, "Intent routing"):
            try:
                prompt = self._prompt_loader.load("intent_routing")

                result = await self._llm.invoke_structured(
                    prompt=prompt,
                    output_model=IntentRoutingOutput,
                    model_type=ModelType.ROUTER,
                    conversation_history=conversation_history,
                )

                logger.info(
                    f"Routed to intent={result.intent.value} "
                    f"confidence={result.confidence:.2f} "
                    f"needs_clarification={result.needs_clarification}"
                )

                return result

            except Exception as e:
                logger.error(f"Intent routing failed: {e}", exc_info=True)
                # Fallback to CHAT_RESPONSE with clarification
                return self._fallback_routing()

    def _fallback_routing(self) -> IntentRoutingOutput:
        """Create fallback routing output when parsing fails."""
        return IntentRoutingOutput(
            intent=IntentType.CHAT_RESPONSE,
            confidence=0.5,
            required_context=[],
            needs_clarification=True,
            clarification_question="죄송해요, 요청을 이해하지 못했어요. 조금 더 자세히 설명해 주시겠어요?",
        )

