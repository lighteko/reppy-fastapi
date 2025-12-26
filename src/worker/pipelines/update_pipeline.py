"""
Update routine pipeline.

Uses update_routine prompt to modify existing workout routines.
"""

import logging
import time
from typing import Any, Dict

from ..contracts import (
    WorkerRequest,
    ResultEvent,
    UpdateRoutineOutput,
)
from .base import BasePipeline

logger = logging.getLogger(__name__)


class UpdatePipeline(BasePipeline):
    """
    Pipeline for UPDATE_ROUTINE intent.
    
    Modifies existing workout routines based on user request.
    """

    async def execute(
        self,
        request: WorkerRequest,
        user_profile: Dict[str, Any],
    ) -> ResultEvent:
        """
        Execute the update pipeline.
        
        Args:
            request: Worker request.
            user_profile: User profile data.
            
        Returns:
            Result event.
        """
        request_id = request.requestId
        
        logger.info(f"[{request_id}] Starting routine update")
        start_time = time.perf_counter()
        
        try:
            # Fetch current routines
            context = await self._context_aggregator.aggregate(
                user_id=request.userId,
                required_context=["active_routines"],
                args={},
                fallback_query="",
                request_id=request_id,
            )
            
            # Load and render prompt
            template = self._prompt_loader.load("update_routine")
            
            # Extract update request from metadata or conversation
            latest_message = self._get_latest_user_message(request.conversation_history)
            user_update_request = request.metadata.get("update_request", {
                "routine_name": request.metadata.get("routine_name", ""),
                "additional_info": latest_message,
            })
            
            available_context = request.metadata.get("available_context", {
                "exercises": [],
                "set_types": [],
            })
            
            # Get the routine to update
            routines = context.get("active_routines", {}).get("routines", [])
            routine_to_update = None
            
            target_name = user_update_request.get("routine_name", "")
            for routine in routines:
                if routine.get("routine_name", "").lower() == target_name.lower():
                    routine_to_update = routine
                    break
            
            # If no specific routine found, use the first one
            if routine_to_update is None and routines:
                routine_to_update = routines[0]
            
            if routine_to_update is None:
                return self._create_error_result(
                    request_id=request_id,
                    code="NO_ROUTINE_FOUND",
                    message="수정할 루틴을 찾을 수 없습니다.",
                    meta={
                        "intent": "UPDATE_ROUTINE",
                        "action": "UPDATE_ROUTINE",
                        "confidence": 0.0,
                    },
                )
            
            variables = {
                "user_profile": user_profile,
                "user_update_request": user_update_request,
                "available_context": available_context,
                "routine_to_update": routine_to_update,
            }
            
            system_prompt, user_prompt = self._prompt_loader.render(template, variables)
            
            # Generate updated routine
            result = await self._gemini.invoke_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=UpdateRoutineOutput,
                use_router_model=False,
                request_id=request_id,
            )
            
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"[{request_id}] Routine update completed in {elapsed:.2f}ms: "
                f"routine={result.routine_name}"
            )
            
            return self._create_success_result(
                request_id=request_id,
                final={"routine": result.model_dump()},
                meta={
                    "intent": "UPDATE_ROUTINE",
                    "action": "UPDATE_ROUTINE",
                    "confidence": 1.0,
                },
            )
            
        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[{request_id}] Routine update failed in {elapsed:.2f}ms: {e}",
                exc_info=True,
            )
            
            return self._create_error_result(
                request_id=request_id,
                code="UPDATE_FAILED",
                message=str(e),
                meta={
                    "intent": "UPDATE_ROUTINE",
                    "action": "UPDATE_ROUTINE",
                    "confidence": 0.0,
                },
            )

