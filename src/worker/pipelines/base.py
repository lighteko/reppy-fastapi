"""
Base pipeline class and shared utilities.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..contracts import (
    WorkerRequest,
    ResultEvent,
    ResultStatus,
    ConversationMessage,
)
from ..context import ContextAggregator
from ..emit import TokenStreamPort, ResultQueuePort
from ..llm import GeminiClient, PromptLoader

logger = logging.getLogger(__name__)


class BasePipeline(ABC):
    """
    Abstract base class for LLM pipelines.
    """

    def __init__(
        self,
        gemini_client: GeminiClient,
        prompt_loader: PromptLoader,
        context_aggregator: ContextAggregator,
        token_stream: TokenStreamPort,
        result_queue: ResultQueuePort,
    ):
        """
        Initialize pipeline with dependencies.
        
        Args:
            gemini_client: Gemini LLM client.
            prompt_loader: Prompt template loader.
            context_aggregator: Context fetching aggregator.
            token_stream: Token streaming port.
            result_queue: Result queue port.
        """
        self._gemini = gemini_client
        self._prompt_loader = prompt_loader
        self._context_aggregator = context_aggregator
        self._token_stream = token_stream
        self._result_queue = result_queue

    @abstractmethod
    async def execute(
        self,
        request: WorkerRequest,
        user_profile: Dict[str, Any],
    ) -> ResultEvent:
        """
        Execute the pipeline.
        
        Args:
            request: The worker request.
            user_profile: User profile data.
            
        Returns:
            Result event to publish.
        """
        pass

    def _get_latest_user_message(
        self,
        conversation_history: List[ConversationMessage],
    ) -> str:
        """
        Get the latest user message from conversation history.
        
        Args:
            conversation_history: List of conversation messages.
            
        Returns:
            Content of the latest user message, or empty string.
        """
        for msg in reversed(conversation_history):
            if msg.role == "user":
                return msg.content
        return ""

    def _conversation_to_list(
        self,
        conversation_history: List[ConversationMessage],
    ) -> List[Dict[str, str]]:
        """
        Convert conversation history to list of dicts.
        
        Args:
            conversation_history: List of ConversationMessage.
            
        Returns:
            List of dict with role and content.
        """
        return [
            {"role": msg.role, "content": msg.content}
            for msg in conversation_history
        ]

    def _create_success_result(
        self,
        request_id: str,
        final: Dict[str, Any],
        meta: Optional[Dict[str, Any]] = None,
    ) -> ResultEvent:
        """Create a success result event."""
        return ResultEvent(
            requestId=request_id,
            status=ResultStatus.SUCCEEDED,
            final=final,
            error=None,
            meta=meta,
        )

    def _create_clarify_result(
        self,
        request_id: str,
        reply: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> ResultEvent:
        """Create a clarification result event."""
        return ResultEvent(
            requestId=request_id,
            status=ResultStatus.CLARIFY,
            final={"reply": reply},
            error=None,
            meta=meta,
        )

    def _create_error_result(
        self,
        request_id: str,
        code: str,
        message: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> ResultEvent:
        """Create an error result event."""
        return ResultEvent(
            requestId=request_id,
            status=ResultStatus.FAILED,
            final=None,
            error={"code": code, "message": message},
            meta=meta,
        )

