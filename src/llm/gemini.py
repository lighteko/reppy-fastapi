"""Gemini LLM client with LangChain integration."""

import json
import logging
from collections.abc import AsyncIterator
from enum import Enum
from typing import Any, TypeVar

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, ValidationError

from src.config import Settings
from src.utils.prompt_loader import PromptTemplate

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ModelType(str, Enum):
    """Model type selection."""

    ROUTER = "router"  # Fast, cheap model for routing/planning
    MAIN = "main"  # Powerful model for generation


class GeminiClient:
    """
    Gemini LLM client using LangChain.
    
    Provides structured output parsing and streaming support.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize Gemini client.
        
        Args:
            settings: Application settings.
        """
        self._settings = settings
        self._router_model: ChatGoogleGenerativeAI | None = None
        self._main_model: ChatGoogleGenerativeAI | None = None

    def _get_model(self, model_type: ModelType) -> ChatGoogleGenerativeAI:
        """Get or create a model instance."""
        if model_type == ModelType.ROUTER:
            if self._router_model is None:
                self._router_model = ChatGoogleGenerativeAI(
                    model=self._settings.gemini_model_router,
                    google_api_key=self._settings.google_api_key,
                    temperature=0.1,  # Low temperature for consistent routing
                    timeout=self._settings.llm_timeout_seconds,
                )
            return self._router_model
        else:
            if self._main_model is None:
                self._main_model = ChatGoogleGenerativeAI(
                    model=self._settings.gemini_model_main,
                    google_api_key=self._settings.google_api_key,
                    temperature=0.7,  # Higher temperature for creative responses
                    timeout=self._settings.llm_timeout_seconds,
                )
            return self._main_model

    async def invoke_structured(
        self,
        prompt: PromptTemplate,
        output_model: type[T],
        model_type: ModelType = ModelType.MAIN,
        **variables: Any,
    ) -> T:
        """
        Invoke LLM with structured output parsing.
        
        Args:
            prompt: Prompt template to use.
            output_model: Pydantic model for output parsing.
            model_type: Which model to use.
            **variables: Variables to render into the prompt.
            
        Returns:
            Parsed output model.
            
        Raises:
            ValueError: If parsing fails after retries.
        """
        model = self._get_model(model_type)
        system_prompt, instruction = prompt.render(**variables)

        # Create messages
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=instruction),
        ]

        # Create parser
        parser = PydanticOutputParser(pydantic_object=output_model)

        try:
            # Invoke model
            response: AIMessage = await model.ainvoke(messages)
            content = response.content

            if isinstance(content, str):
                # Clean up response - remove markdown code blocks if present
                content = self._clean_json_response(content)
                
                # Parse JSON
                try:
                    data = json.loads(content)
                    return output_model.model_validate(data)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error: {e}")
                    # Try parser as fallback
                    return parser.parse(content)
            else:
                raise ValueError(f"Unexpected response type: {type(content)}")

        except ValidationError as e:
            logger.error(f"Validation error parsing LLM output: {e}")
            raise ValueError(f"Failed to parse LLM output: {e}") from e

    async def invoke_streaming(
        self,
        prompt: PromptTemplate,
        model_type: ModelType = ModelType.MAIN,
        **variables: Any,
    ) -> AsyncIterator[str]:
        """
        Invoke LLM with streaming response.
        
        Args:
            prompt: Prompt template to use.
            model_type: Which model to use.
            **variables: Variables to render into the prompt.
            
        Yields:
            Token strings as they are generated.
        """
        model = self._get_model(model_type)
        system_prompt, instruction = prompt.render(**variables)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=instruction),
        ]

        async for chunk in model.astream(messages):
            if hasattr(chunk, "content") and chunk.content:
                yield str(chunk.content)

    async def invoke_streaming_structured(
        self,
        prompt: PromptTemplate,
        output_model: type[T],
        model_type: ModelType = ModelType.MAIN,
        **variables: Any,
    ) -> tuple[AsyncIterator[str], "StreamingCollector[T]"]:
        """
        Invoke LLM with streaming, collecting for structured parsing.
        
        Args:
            prompt: Prompt template to use.
            output_model: Pydantic model for final parsing.
            model_type: Which model to use.
            **variables: Variables to render into the prompt.
            
        Returns:
            Tuple of (token iterator, collector for final result).
        """
        collector: StreamingCollector[T] = StreamingCollector(output_model)
        
        async def token_generator() -> AsyncIterator[str]:
            async for token in self.invoke_streaming(prompt, model_type, **variables):
                collector.add_token(token)
                yield token

        return token_generator(), collector

    def _clean_json_response(self, content: str) -> str:
        """
        Clean up LLM response to extract JSON.
        
        Args:
            content: Raw LLM response.
            
        Returns:
            Cleaned JSON string.
        """
        content = content.strip()

        # Remove markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]

        if content.endswith("```"):
            content = content[:-3]

        return content.strip()


class StreamingCollector[T: BaseModel]:
    """
    Collects streaming tokens and parses final result.
    
    Type parameter T must be a Pydantic BaseModel.
    """

    def __init__(self, output_model: type[T]) -> None:
        """
        Initialize collector.
        
        Args:
            output_model: Pydantic model for parsing.
        """
        self._output_model = output_model
        self._tokens: list[str] = []
        self._result: T | None = None

    def add_token(self, token: str) -> None:
        """Add a token to the collection."""
        self._tokens.append(token)

    def get_full_content(self) -> str:
        """Get the complete collected content."""
        return "".join(self._tokens)

    def parse(self) -> T:
        """
        Parse the collected content into the output model.
        
        Returns:
            Parsed output model.
            
        Raises:
            ValueError: If parsing fails.
        """
        if self._result is not None:
            return self._result

        content = self.get_full_content().strip()

        # Clean up markdown
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            data = json.loads(content)
            self._result = self._output_model.model_validate(data)
            return self._result
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValueError(f"Failed to parse streaming result: {e}") from e

