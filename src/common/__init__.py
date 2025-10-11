"""Shared utilities and clients for the Reppy AI service."""

from .clients import get_openai_client, get_qdrant_client
from .express_client import ExpressAPIClient
from .models import (
    ChatMessage,
    ChatRequest,
    GenerateProgramJob,
    PromptTemplate,
    RoutineBatch,
    ensure_required_variables,
)
from .orchestrator import RAGOrchestrator, load_prompt_template

__all__ = [
    "ChatMessage",
    "ChatRequest",
    "ExpressAPIClient",
    "GenerateProgramJob",
    "PromptTemplate",
    "RAGOrchestrator",
    "RoutineBatch",
    "ensure_required_variables",
    "get_openai_client",
    "get_qdrant_client",
    "load_prompt_template",
]
