# /app/core/lifespan.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.rag.chain import create_rag_chain
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    This function is executed on application startup and shutdown.
    It's the ideal place to initialize resources like models, database connections, etc.
    """
    logger.info("Application startup: Initializing RAG chain...")

    # On startup, create the RAG chain and store it in the app's state.
    # This ensures the model and retriever are loaded only once, improving performance.
    try:
        app.state.rag_chain = create_rag_chain()
        logger.info("RAG chain initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize RAG chain: {e}")
        # You might want to handle this more gracefully, e.g., by preventing the app from starting.
        app.state.rag_chain = None

    yield  # The application is now running

    # On shutdown, you can add cleanup code here if needed.
    logger.info("Application shutdown: Cleaning up resources...")
    app.state.rag_chain = None  # Clear the state
