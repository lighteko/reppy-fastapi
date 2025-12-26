"""
Structured output parser with fallback handling.
"""

import json
import logging
import re
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class StructuredOutputParser:
    """
    Parser for structured LLM outputs with fallback handling.
    
    Attempts to parse JSON from LLM responses and validate against
    Pydantic models, with graceful fallback on failures.
    """

    @staticmethod
    def extract_json(text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from text that may contain markdown or other content.
        
        Args:
            text: Raw text that may contain JSON.
            
        Returns:
            Parsed JSON dict or None if extraction fails.
        """
        # Try direct parsing first
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        
        # Try extracting from markdown code blocks
        patterns = [
            r"```json\s*([\s\S]*?)\s*```",
            r"```\s*([\s\S]*?)\s*```",
            r"\{[\s\S]*\}",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    json_str = match.group(1) if "```" in pattern else match.group(0)
                    return json.loads(json_str.strip())
                except (json.JSONDecodeError, IndexError):
                    continue
        
        return None

    @staticmethod
    def parse(
        text: str,
        schema: Type[T],
        request_id: str = "",
    ) -> tuple[Optional[T], Optional[str]]:
        """
        Parse text into a Pydantic model.
        
        Args:
            text: Raw LLM output text.
            schema: Pydantic model class.
            request_id: Request ID for logging.
            
        Returns:
            Tuple of (parsed_model, error_message).
            If successful, error_message is None.
            If failed, parsed_model is None.
        """
        # Extract JSON
        json_data = StructuredOutputParser.extract_json(text)
        
        if json_data is None:
            error = f"Failed to extract JSON from LLM output"
            logger.warning(f"[{request_id}] {error}: {text[:200]}...")
            return None, error
        
        # Validate against schema
        try:
            parsed = schema.model_validate(json_data)
            return parsed, None
        except ValidationError as e:
            error = f"Validation failed: {e}"
            logger.warning(f"[{request_id}] {error}")
            return None, error

    @staticmethod
    def parse_with_fallback(
        text: str,
        schema: Type[T],
        fallback: T,
        request_id: str = "",
    ) -> T:
        """
        Parse text into a Pydantic model with fallback.
        
        Args:
            text: Raw LLM output text.
            schema: Pydantic model class.
            fallback: Fallback instance to return on failure.
            request_id: Request ID for logging.
            
        Returns:
            Parsed model or fallback.
        """
        parsed, error = StructuredOutputParser.parse(text, schema, request_id)
        
        if parsed is not None:
            return parsed
        
        logger.warning(f"[{request_id}] Using fallback due to parsing error: {error}")
        return fallback

