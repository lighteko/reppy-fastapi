"""LLM-based action router using intent classification prompt."""

import json
from typing import Any, Dict, List, Optional, Tuple
import asyncio

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from src.common.utils.prompts import load_prompt, list_prompts
from src.config import get_config


class LLMActionRouter:
    """Routes user inputs using LLM-based intent classification."""
    
    # Intent to prompt key mapping
    INTENT_TO_PROMPT = {
        "GENERATE_ROUTINE": "generate_program",
        "UPDATE_ROUTINE": "update_routine",
        "CHAT_RESPONSE": "chat_response",
    }
    
    def __init__(self, llm: Optional[Any] = None, config: Optional[Any] = None):
        """Initialize the LLM-based router.
        
        Args:
            llm: Optional LLM instance. If None, creates ChatOpenAI.
            config: Optional configuration object.
        """
        self.config = config or get_config()
        
        # Initialize LLM with lightweight model for routing
        if llm is None:
            self.llm = ChatOpenAI(
                model=self.config.router_llm_model,  # Use lightweight model
                temperature=0.0,  # Use 0 for classification
                max_tokens=100,  # Only need a short response
                openai_api_key=self.config.openai_api_key,
                timeout=self.config.llm_timeout,
            )
            logger.info(f"Router initialized with model: {self.config.router_llm_model}")
        else:
            self.llm = llm
        
        # Load routing prompt
        try:
            self.routing_prompt = load_prompt("action_routing")
            logger.info("Loaded LLM-based action routing prompt")
        except FileNotFoundError:
            logger.warning("action_routing.yaml not found, falling back to pattern matching")
            self.routing_prompt = None
        
        self.available_prompts = list_prompts()
        logger.info(f"LLM Router initialized with {len(self.available_prompts)} available prompts")
    
    def _format_conversation_history(self, input_text: str, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Format conversation history for the routing prompt.
        
        Args:
            input_text: Current user input.
            context: Additional context that might contain conversation history.
            
        Returns:
            List of conversation messages.
        """
        # Check if context already has conversation_history
        if "conversation_history" in context:
            history = context["conversation_history"]
            if isinstance(history, list):
                return history
        
        # Otherwise, create a simple history with just the current message
        return [
            {
                "role": "user",
                "content": input_text,
            }
        ]
    
    def _parse_intent_from_response(self, response_text: str) -> str:
        """Parse intent from LLM response.
        
        Args:
            response_text: Raw LLM response.
            
        Returns:
            Intent string (GENERATE_ROUTINE, UPDATE_ROUTINE, or CHAT_RESPONSE).
        """
        # Remove markdown code blocks if present
        text = response_text.strip()
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                text = text[start:end].strip()
        
        # Try to parse as JSON
        try:
            data = json.loads(text)
            intent = data.get("intent", "CHAT_RESPONSE")
            
            # Validate intent
            if intent in self.INTENT_TO_PROMPT:
                return intent
            else:
                logger.warning(f"Invalid intent '{intent}', defaulting to CHAT_RESPONSE")
                return "CHAT_RESPONSE"
                
        except json.JSONDecodeError:
            # Try to find intent in text
            text_upper = text.upper()
            if "GENERATE_ROUTINE" in text_upper:
                return "GENERATE_ROUTINE"
            elif "UPDATE_ROUTINE" in text_upper:
                return "UPDATE_ROUTINE"
            else:
                logger.warning(f"Failed to parse intent from response: {text[:100]}")
                return "CHAT_RESPONSE"
    
    async def route(
        self,
        input_text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """Route input using LLM-based intent classification.
        
        Args:
            input_text: User input text.
            context: Optional additional context (conversation history, user data, etc.).
            
        Returns:
            Tuple of (selected_prompt_key, metadata_dict).
        """
        context = context or {}
        
        # Check if we have the routing prompt
        if self.routing_prompt is None:
            logger.warning("No routing prompt available, defaulting to chat_response")
            return "chat_response", {"method": "fallback", "intent": "CHAT_RESPONSE"}
        
        try:
            # Format conversation history
            conversation_history = self._format_conversation_history(input_text, context)
            conversation_history_json = json.dumps(conversation_history, indent=2)
            
            # Build prompt from YAML
            role = self.routing_prompt.get("role", "")
            instruction = self.routing_prompt.get("instruction", "")
            
            # Replace variables BEFORE creating messages
            # This avoids LangChain trying to interpret JSON as template variables
            instruction_filled = instruction.replace("{conversation_history_json}", conversation_history_json)
            
            # Create system message
            system_message = f"{role}\n\n{instruction_filled}"
            
            # Directly create messages without template parsing
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content="Classify the intent of the latest message in the conversation history."),
            ]
            
            # Call LLM directly
            response = await self.llm.ainvoke(messages)
            
            # Parse intent from response
            intent = self._parse_intent_from_response(response.content)
            
            # Map to prompt key
            prompt_key = self.INTENT_TO_PROMPT.get(intent, "chat_response")
            
            logger.info(f"LLM classified intent as: {intent} -> {prompt_key}")
            
            return prompt_key, {
                "method": "llm_classification",
                "intent": intent,
                "prompt_key": prompt_key,
                "llm_response": response.content[:200],  # Truncate for logging
            }
            
        except Exception as e:
            logger.error(f"LLM routing failed: {e}")
            # Fallback to safe default
            return "chat_response", {
                "method": "error_fallback",
                "error": str(e),
            }
    
    def route_sync(
        self,
        input_text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """Synchronous wrapper for route method.
        
        Args:
            input_text: User input text.
            context: Optional additional context.
            
        Returns:
            Tuple of (selected_prompt_key, metadata_dict).
        """
        # Run in new event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.route(input_text, context)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(self.route(input_text, context))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self.route(input_text, context))


# Singleton instance
_llm_router: Optional[LLMActionRouter] = None


def get_llm_router(llm: Optional[Any] = None) -> LLMActionRouter:
    """Get the singleton LLM router instance.
    
    Args:
        llm: Optional LLM instance.
        
    Returns:
        LLMActionRouter instance.
    """
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMActionRouter(llm=llm)
    return _llm_router


async def route_input_llm(
    input_text: str,
    context: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Route an input using LLM-based classification (convenience function).
    
    Args:
        input_text: User input text.
        context: Optional context.
        
    Returns:
        Tuple of (selected_prompt_key, metadata_dict).
    """
    router = get_llm_router()
    return await router.route(input_text, context)


def route_input_llm_sync(
    input_text: str,
    context: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Route an input using LLM synchronously (convenience function).
    
    Args:
        input_text: User input text.
        context: Optional context.
        
    Returns:
        Tuple of (selected_prompt_key, metadata_dict).
    """
    router = get_llm_router()
    return router.route_sync(input_text, context)

