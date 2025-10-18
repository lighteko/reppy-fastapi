"""Tests for LLM-based action router."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.common import LLMActionRouter, route_input_llm


class TestLLMActionRouter:
    """Test cases for LLM-based action router."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        llm = AsyncMock()
        return llm
    
    @pytest.fixture
    def router(self, mock_llm):
        """Create a router with mock LLM."""
        with patch("src.common.pipeline.router.load_prompt") as mock_load:
            # Mock the routing prompt
            mock_load.return_value = {
                "role": "You are an intent classifier.",
                "instruction": "Classify the intent: {conversation_history_json}",
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "enum": ["GENERATE_ROUTINE", "UPDATE_ROUTINE", "CHAT_RESPONSE"]
                        }
                    }
                }
            }
            router = LLMActionRouter(llm=mock_llm)
            return router
    
    @pytest.mark.asyncio
    async def test_route_generate_program(self, router, mock_llm):
        """Test routing to generate_program."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = '{"intent": "GENERATE_ROUTINE"}'
        mock_llm.ainvoke.return_value = mock_response
        
        prompt_key, metadata = await router.route("I want a new workout program")
        
        assert prompt_key == "generate_program"
        assert metadata["intent"] == "GENERATE_ROUTINE"
        assert metadata["method"] == "llm_classification"
    
    @pytest.mark.asyncio
    async def test_route_update_routine(self, router, mock_llm):
        """Test routing to update_routine."""
        mock_response = MagicMock()
        mock_response.content = '{"intent": "UPDATE_ROUTINE"}'
        mock_llm.ainvoke.return_value = mock_response
        
        prompt_key, metadata = await router.route("Can you make my push day harder?")
        
        assert prompt_key == "update_routine"
        assert metadata["intent"] == "UPDATE_ROUTINE"
    
    @pytest.mark.asyncio
    async def test_route_chat_response(self, router, mock_llm):
        """Test routing to chat_response."""
        mock_response = MagicMock()
        mock_response.content = '{"intent": "CHAT_RESPONSE"}'
        mock_llm.ainvoke.return_value = mock_response
        
        prompt_key, metadata = await router.route("How do I do a squat?")
        
        assert prompt_key == "chat_response"
        assert metadata["intent"] == "CHAT_RESPONSE"
    
    @pytest.mark.asyncio
    async def test_route_with_conversation_history(self, router, mock_llm):
        """Test routing with conversation history context."""
        mock_response = MagicMock()
        mock_response.content = '{"intent": "UPDATE_ROUTINE"}'
        mock_llm.ainvoke.return_value = mock_response
        
        context = {
            "conversation_history": [
                {"role": "user", "content": "What's a good chest exercise?"},
                {"role": "assistant", "content": "Bench press is great."},
                {"role": "user", "content": "Add that to my routine."},
            ]
        }
        
        prompt_key, metadata = await router.route("Add that to my routine.", context)
        
        assert prompt_key == "update_routine"
        assert mock_llm.ainvoke.called
    
    @pytest.mark.asyncio
    async def test_parse_intent_from_markdown_json(self, router, mock_llm):
        """Test parsing intent from markdown-wrapped JSON."""
        mock_response = MagicMock()
        mock_response.content = '```json\n{"intent": "GENERATE_ROUTINE"}\n```'
        mock_llm.ainvoke.return_value = mock_response
        
        prompt_key, metadata = await router.route("Make me a program")
        
        assert prompt_key == "generate_program"
        assert metadata["intent"] == "GENERATE_ROUTINE"
    
    @pytest.mark.asyncio
    async def test_parse_intent_from_text(self, router, mock_llm):
        """Test parsing intent from plain text response."""
        mock_response = MagicMock()
        mock_response.content = "The intent is UPDATE_ROUTINE"
        mock_llm.ainvoke.return_value = mock_response
        
        prompt_key, metadata = await router.route("Change my workout")
        
        assert prompt_key == "update_routine"
        assert metadata["intent"] == "UPDATE_ROUTINE"
    
    @pytest.mark.asyncio
    async def test_invalid_intent_defaults_to_chat(self, router, mock_llm):
        """Test that invalid intent defaults to chat_response."""
        mock_response = MagicMock()
        mock_response.content = '{"intent": "INVALID_INTENT"}'
        mock_llm.ainvoke.return_value = mock_response
        
        prompt_key, metadata = await router.route("Something random")
        
        assert prompt_key == "chat_response"
        # Should still parse but default
        assert metadata["method"] == "llm_classification"
    
    @pytest.mark.asyncio
    async def test_llm_error_fallback(self, router, mock_llm):
        """Test fallback when LLM call fails."""
        mock_llm.ainvoke.side_effect = Exception("API error")
        
        prompt_key, metadata = await router.route("Test input")
        
        assert prompt_key == "chat_response"
        assert metadata["method"] == "error_fallback"
        assert "error" in metadata
    
    @pytest.mark.asyncio
    async def test_no_routing_prompt_fallback(self, mock_llm):
        """Test fallback when routing prompt is not found."""
        with patch("src.common.pipeline.router.load_prompt") as mock_load:
            mock_load.side_effect = FileNotFoundError("action_routing.yaml not found")
            router = LLMActionRouter(llm=mock_llm)
            
            prompt_key, metadata = await router.route("Test input")
            
            assert prompt_key == "chat_response"
            assert metadata["method"] == "fallback"
    
    def test_intent_to_prompt_mapping(self, router):
        """Test the intent to prompt key mapping."""
        assert router.INTENT_TO_PROMPT["GENERATE_ROUTINE"] == "generate_program"
        assert router.INTENT_TO_PROMPT["UPDATE_ROUTINE"] == "update_routine"
        assert router.INTENT_TO_PROMPT["CHAT_RESPONSE"] == "chat_response"
    
    def test_format_conversation_history_from_context(self, router):
        """Test formatting conversation history from context."""
        context = {
            "conversation_history": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"},
            ]
        }
        
        history = router._format_conversation_history("Test", context)
        
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
    
    def test_format_conversation_history_single_message(self, router):
        """Test formatting when no context provided."""
        history = router._format_conversation_history("Test input", {})
        
        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Test input"


@pytest.mark.asyncio
async def test_route_input_llm_convenience_function():
    """Test the convenience function for routing."""
    with patch("src.common.pipeline.router.get_llm_router") as mock_get:
        mock_router = AsyncMock()
        mock_router.route.return_value = ("chat_response", {"method": "llm"})
        mock_get.return_value = mock_router
        
        result = await route_input_llm("Test input")
        
        assert result == ("chat_response", {"method": "llm"})
        mock_router.route.assert_called_once()

