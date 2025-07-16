from fastapi import APIRouter
from app.api.v1.endpoints import rag

# Create the main router for the v1 API
api_router = APIRouter()

# Include the rag endpoint router
# All routes from the rag module will be included here.
api_router.include_router(rag.router, prefix="/rag", tags=["RAG"])