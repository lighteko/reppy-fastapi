"""Program generation pipeline."""

import logging
from typing import Any

from src.config import Settings
from src.contracts.schemas import GenerateProgramOutput
from src.llm.gemini import GeminiClient, ModelType
from src.utils.logging import latency_log
from src.utils.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class GeneratePipeline:
    """
    Program generation pipeline.
    
    Generates new workout programs based on user profile and context.
    """

    def __init__(
        self,
        settings: Settings,
        prompt_loader: PromptLoader,
        llm_client: GeminiClient,
    ) -> None:
        """
        Initialize generation pipeline.
        
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
        job_context: dict[str, Any],
        available_context: dict[str, Any],
        current_routines: list[dict[str, Any]] | None = None,
    ) -> GenerateProgramOutput:
        """
        Execute program generation pipeline.
        
        Args:
            user_profile: User profile with goals, experience, etc.
            job_context: Generation job context (dates, name, etc.).
            available_context: Available exercises and set types.
            current_routines: Current routines for progression (optional).
            
        Returns:
            Generated program output.
            
        Raises:
            ValueError: If generation fails.
        """
        with latency_log(logger, "Program generation"):
            try:
                prompt = self._prompt_loader.load("generate_program")

                result = await self._llm.invoke_structured(
                    prompt=prompt,
                    output_model=GenerateProgramOutput,
                    model_type=ModelType.MAIN,
                    user_profile=user_profile,
                    job_context=job_context,
                    available_context=available_context,
                    current_routines=current_routines or [],
                )

                logger.info(
                    f"Generated program with {len(result.routines)} routines"
                )

                return result

            except Exception as e:
                logger.error(f"Program generation failed: {e}", exc_info=True)
                raise ValueError(f"Failed to generate program: {e}") from e

