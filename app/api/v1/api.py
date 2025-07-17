# /app/api/v1/api.py
from fastapi import APIRouter
# Renamed from 'rag' to 'reppy' to better suit the application
from app.reppy import endpoints as reppy_endpoints

api_router = APIRouter()

# Include the main application endpoints
api_router.include_router(reppy_endpoints.router, prefix="/reppy", tags=["Reppy"])
