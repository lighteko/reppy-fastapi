"""
Gemini client using LangChain integration.

Provides both streaming and non-streaming LLM calls with structured output support.
"""

import logging
import time
from typing import Any, AsyncIterator, Dict, Optional, Type, TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from ..config import settings
from .prompt_loader import PromptTemplate

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GeminiClient:
    """
    LangChain-based Gemini client.
    
    Supports:
    - Structured output with Pydantic models
    - Streaming responses
    - Separate router/main models for cost optimization
    """

    def __init__(self):
        """Initialize Gemini client with models from settings."""
        self._router_model: Optional[ChatGoogleGenerativeAI] = None
        self._main_model: Optional[ChatGoogleGenerativeAI] = None

    def _get_router_model(self) -> ChatGoogleGenerativeAI:
        """Get or create router model (Flash for cost efficiency)."""
        if self._router_model is None:
            self._router_model = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL_ROUTER,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.1,
                max_retries=2,
            )
        return self._router_model

    def _get_main_model(self) -> ChatGoogleGenerativeAI:
        """Get or create main model (Pro for quality)."""
        if self._main_model is None:
            self._main_model = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL_MAIN,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.7,
                max_retries=2,
            )
        return self._main_model

    async def invoke_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: Type[T],
        use_router_model: bool = False,
        request_id: str = "",
    ) -> T:
        """
        Invoke LLM with structured output.
        
        Args:
            system_prompt: System message content.
            user_prompt: User message content.
            output_schema: Pydantic model class for output.
            use_router_model: If True, use Flash model; else Pro.
            request_id: Request ID for logging.
            
        Returns:
            Parsed output matching the schema.
        """
        model = self._get_router_model() if use_router_model else self._get_main_model()
        
        # Create structured output model
        structured_model = model.with_structured_output(output_schema)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        
        start_time = time.perf_counter()
        
        try:
            result = await structured_model.ainvoke(messages)
            elapsed = (time.perf_counter() - start_time) * 1000
            
            model_name = settings.GEMINI_MODEL_ROUTER if use_router_model else settings.GEMINI_MODEL_MAIN
            logger.info(
                f"[{request_id}] LLM structured call completed: "
                f"model={model_name}, elapsed={elapsed:.2f}ms"
            )
            
            return result
            
        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[{request_id}] LLM structured call failed: "
                f"elapsed={elapsed:.2f}ms, error={e}"
            )
            raise

    async def invoke_text(
        self,
        system_prompt: str,
        user_prompt: str,
        use_router_model: bool = False,
        request_id: str = "",
    ) -> str:
        """
        Invoke LLM for plain text response.
        
        Args:
            system_prompt: System message content.
            user_prompt: User message content.
            use_router_model: If True, use Flash model; else Pro.
            request_id: Request ID for logging.
            
        Returns:
            Text response content.
        """
        model = self._get_router_model() if use_router_model else self._get_main_model()
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        
        start_time = time.perf_counter()
        
        try:
            result = await model.ainvoke(messages)
            elapsed = (time.perf_counter() - start_time) * 1000
            
            model_name = settings.GEMINI_MODEL_ROUTER if use_router_model else settings.GEMINI_MODEL_MAIN
            logger.info(
                f"[{request_id}] LLM text call completed: "
                f"model={model_name}, elapsed={elapsed:.2f}ms"
            )
            
            return result.content
            
        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[{request_id}] LLM text call failed: "
                f"elapsed={elapsed:.2f}ms, error={e}"
            )
            raise

    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        use_router_model: bool = False,
        request_id: str = "",
    ) -> AsyncIterator[str]:
        """
        Stream LLM response.
        
        Args:
            system_prompt: System message content.
            user_prompt: User message content.
            use_router_model: If True, use Flash model; else Pro.
            request_id: Request ID for logging.
            
        Yields:
            Token chunks as they arrive.
        """
        model = self._get_router_model() if use_router_model else self._get_main_model()
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        
        start_time = time.perf_counter()
        token_count = 0
        
        try:
            async for chunk in model.astream(messages):
                if chunk.content:
                    token_count += 1
                    yield chunk.content
            
            elapsed = (time.perf_counter() - start_time) * 1000
            model_name = settings.GEMINI_MODEL_ROUTER if use_router_model else settings.GEMINI_MODEL_MAIN
            logger.info(
                f"[{request_id}] LLM stream completed: "
                f"model={model_name}, chunks={token_count}, elapsed={elapsed:.2f}ms"
            )
            
        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[{request_id}] LLM stream failed: "
                f"elapsed={elapsed:.2f}ms, error={e}"
            )
            raise


# Global client instance
_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """Get the global Gemini client instance."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client

