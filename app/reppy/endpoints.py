# /app/reppy/endpoints.py
from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
import json

from app.reppy.schemas import RoutineGenerationRequest, RoutineResponse, CoachRequest, CoachResponse
from app.reppy.chains import create_routine_generation_chain, create_coach_chain
from app.core.state import AppState

router = APIRouter()


@router.post("/generate_routine", response_model=RoutineResponse)
async def generate_routine_endpoint(req: Request, routine_request: RoutineGenerationRequest):
    """
    Generates a personalized fitness routine based on the user's profile.
    """
    try:
        state: AppState = req.app.state
        generation_chain = create_routine_generation_chain(state)

        # The chain expects the user profile as a dictionary
        result = generation_chain.invoke(routine_request.user_profile.model_dump())

        # The result from the chain is a JSON string, which we parse into a dict
        return RoutineResponse(routine=json.loads(result))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse AI model's JSON output: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during routine generation: {str(e)}")


@router.post("/coach_chat")
async def coach_chat_endpoint(req: Request, coach_request: CoachRequest):
    """
    Handles interactive chat with the AI coach.
    This is a streaming endpoint.
    """
    state: AppState = req.app.state
    coach_chain = create_coach_chain(state)

    async def event_generator():
        try:
            # The chain expects a dictionary containing the user's message, history, and profile
            async for chunk in coach_chain.astream({
                "user_message": coach_request.user_message,
                "chat_history": coach_request.chat_history,
                "user_profile": coach_request.user_profile.model_dump()
            }):
                # The chunk is already a string from the StrOutputParser
                if chunk:
                    yield json.dumps({"ai_message_chunk": chunk})
        except Exception as e:
            error_message = {"error": f"An error occurred during chat streaming: {str(e)}"}
            yield json.dumps(error_message)

    return EventSourceResponse(event_generator())
