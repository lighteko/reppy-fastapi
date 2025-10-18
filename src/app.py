"""FastAPI application initialization."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api.routers import router
from src.config import get_config
from src.common import setup_logging


# Initialize logging
setup_logging()

# Get config
config = get_config()

# Create FastAPI app
app = FastAPI(
    title="Reppy RAG Pipeline",
    description="AI-powered fitness coaching with LangChain RAG",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Starting Reppy RAG Pipeline API")
    logger.info(f"LLM Model: {config.llm_model}")
    logger.info(f"Qdrant URL: {config.qdrant_url}")
    logger.info(f"Express API: {config.express_base_url}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Shutting down Reppy RAG Pipeline API")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Reppy RAG Pipeline",
        "version": "1.0.0",
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

