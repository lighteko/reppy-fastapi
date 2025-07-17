# /app/reppy/chains.py
from langchain_core.runnables import Runnable
from langchain_core.output_parsers import StrOutputParser
from app.reppy.prompts import get_routine_generation_prompt, get_coach_prompt
from app.core.state import AppState


def create_routine_generation_chain(app_state: AppState) -> Runnable:
    """
    Creates the chain responsible for generating a structured workout routine.
    """
    generator_model = app_state.models["routine_generator"]
    prompt = get_routine_generation_prompt()

    # The chain takes a user profile, formats the prompt, and returns the raw JSON string from the model.
    chain = prompt | generator_model | StrOutputParser()
    return chain


def create_coach_chain(app_state: AppState) -> Runnable:
    """
    Creates the chain responsible for the interactive AI coach's responses.
    """
    coach_model = app_state.models["coach"]
    prompt = get_coach_prompt()

    # The chain takes user message, history, and profile, formats the prompt, and returns the AI's response string.
    chain = prompt | coach_model | StrOutputParser()
    return chain
