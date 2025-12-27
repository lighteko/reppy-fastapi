"""Routine update pipeline."""

import logging
from typing import Any

from src.config import Settings
from src.contracts.schemas import UpdateRoutineOutput
from src.llm.gemini import GeminiClient, ModelType
from src.utils.logging import latency_log
from src.utils.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class UpdatePipeline:
    """
    Routine update pipeline.
    
    Updates existing workout routines based on user requests.
    """

    def __init__(
        self,
        settings: Settings,
        prompt_loader: PromptLoader,
        llm_client: GeminiClient,
    ) -> None:
        """
        Initialize update pipeline.
        
        Args:
            settings: Application settings.
            prompt_loader: Prompt template loader.
            llm_client: Gemini LLM client.
        """
        self._settings = settings
        self._prompt_loader = prompt_loader
        self._llm = llm_client

    async def execute(
        self,
        user_profile: dict[str, Any],
        user_update_request: dict[str, Any],
        available_context: dict[str, Any],
        routine_to_update: dict[str, Any],
    ) -> UpdateRoutineOutput:
        """
        Execute routine update pipeline.
        
        Args:
            user_profile: User profile with goals, experience, etc.
            user_update_request: User's update request (routine_name, additional_info).
            available_context: Available exercises and set types.
            routine_to_update: The routine to modify.
            
        Returns:
            Updated routine output.
            
        Raises:
            ValueError: If update fails.
        """
        with latency_log(logger, "Routine update"):
            try:
                prompt = self._prompt_loader.load("update_routine")

                result = await self._llm.invoke_structured(
                    prompt=prompt,
                    output_model=UpdateRoutineOutput,
                    model_type=ModelType.MAIN,
                    user_profile=user_profile,
                    user_update_request=user_update_request,
                    available_context=available_context,
                    routine_to_update=routine_to_update,
                )

                logger.info(
                    f"Updated routine '{result.routine_name}' "
                    f"with {len(result.plans)} exercises"
                )

                return result

            except Exception as e:
                logger.error(f"Routine update failed: {e}", exc_info=True)
                raise ValueError(f"Failed to update routine: {e}") from e

