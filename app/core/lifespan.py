# /app/core/lifespan.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.core.state import AppState
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan manager to initialize and store the AI models on application startup.
    """
    logger.info("Application startup: Initializing AI models for Reppy...")

    app.state = AppState()

    try:
        # Initialize the two required models for Reppy's features
        routine_generator_model = ChatOpenAI(
            model=settings.ROUTINE_GENERATOR_LLM,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY
        )
        coach_model = ChatOpenAI(
            model=settings.COACH_LLM,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY
        )
        # Store them in the state dictionary with clear keys
        app.state.models = {
            "routine_generator": routine_generator_model,
            "coach": coach_model
        }

        logger.info("AI models initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize AI models: {e}")

    yield

    logger.info("Application shutdown.")
