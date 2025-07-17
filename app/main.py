from fastapi import FastAPI
from app.core.lifespan import lifespan
from app.api.v1.api import api_router
from app.core.config import settings

# The main FastAPI application instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan # Use the lifespan manager
)

# Include the API router
# This makes all routes defined in api_router available under the /api/v1 prefix
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["Root"])
async def read_root():
    """
    A simple root endpoint to confirm the server is running.
    """
    return {"message": "Welcome to the LangChain RAG API Server"}
