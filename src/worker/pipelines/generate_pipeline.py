"""
Generate routine/program pipeline.

Uses generate_program prompt to create new workout programs.
"""

import logging
import time
from typing import Any, Dict

from ..contracts import (
    WorkerRequest,
    ResultEvent,
    GenerateProgramOutput,
)
from .base import BasePipeline

logger = logging.getLogger(__name__)


class GeneratePipeline(BasePipeline):
    """
    Pipeline for GENERATE_ROUTINE intent.
    
    Creates new workout programs based on user profile and context.
    """

    async def execute(
        self,
        request: WorkerRequest,
        user_profile: Dict[str, Any],
    ) -> ResultEvent:
        """
        Execute the generate pipeline.
        
        Args:
            request: Worker request.
            user_profile: User profile data.
            
        Returns:
            Result event.
        """
        request_id = request.requestId
        
        logger.info(f"[{request_id}] Starting program generation")
        start_time = time.perf_counter()
        
        try:
            # Fetch context needed for generation
            context = await self._context_aggregator.aggregate(
                user_id=request.userId,
                required_context=["active_routines"],
                args={},
                fallback_query="",
                request_id=request_id,
            )
            
            # Load and render prompt
            template = self._prompt_loader.load("generate_program")
            
            # Extract job context from metadata
            job_context = request.metadata.get("job_context", {})
            available_context = request.metadata.get("available_context", {
                "exercises": [],
                "set_types": [],
            })
            
            current_routines = context.get("active_routines", {}).get("routines", [])
            
            variables = {
                "user_profile": user_profile,
                "job_context": job_context,
                "available_context": available_context,
                "current_routines": current_routines,
            }
            
            system_prompt, user_prompt = self._prompt_loader.render(template, variables)
            
            # Generate program
            result = await self._gemini.invoke_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=GenerateProgramOutput,
                use_router_model=False,
                request_id=request_id,
            )
            
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"[{request_id}] Program generation completed in {elapsed:.2f}ms: "
                f"routines={len(result.routines)}"
            )
            
            return self._create_success_result(
                request_id=request_id,
                final={"program": result.model_dump()},
                meta={
                    "intent": "GENERATE_ROUTINE",
                    "action": "GENERATE_PROGRAM",
                    "confidence": 1.0,
                },
            )
            
        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[{request_id}] Program generation failed in {elapsed:.2f}ms: {e}",
                exc_info=True,
            )
            
            return self._create_error_result(
                request_id=request_id,
                code="GENERATION_FAILED",
                message=str(e),
                meta={
                    "intent": "GENERATE_ROUTINE",
                    "action": "GENERATE_PROGRAM",
                    "confidence": 0.0,
                },
            )

