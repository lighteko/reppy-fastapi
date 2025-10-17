"""Tests for action router."""

import pytest

from src.common.action_router import ActionRouter, route_input


def test_router_initialization():
    """Test router initialization."""
    router = ActionRouter()
    
    assert router is not None
    assert len(router.available_prompts) >= 3


def test_route_generate_program():
    """Test routing to generate_program."""
    router = ActionRouter()
    
    # Test various inputs that should route to generate_program
    test_inputs = [
        "I want to generate a new program",
        "Create a routine for me",
        "Help me build a new mesocycle",
        "Can you design a new workout block?",
    ]
    
    for input_text in test_inputs:
        prompt_key, scores = router.route(input_text)
        assert prompt_key == "generate_program", f"Failed for input: {input_text}"


def test_route_update_routine():
    """Test routing to update_routine."""
    router = ActionRouter()
    
    # Test various inputs that should route to update_routine
    test_inputs = [
        "I need to update my routine",
        "Can you modify my workout?",
        "Make my bench press harder",
        "Swap out the overhead press",
        "Increase the weight on squats",
    ]
    
    for input_text in test_inputs:
        prompt_key, scores = router.route(input_text)
        assert prompt_key == "update_routine", f"Failed for input: {input_text}"


def test_route_chat_response():
    """Test routing to chat_response (fallback)."""
    router = ActionRouter()
    
    # Test various inputs that should route to chat_response
    test_inputs = [
        "What's a good exercise for chest?",
        "How do I do a proper squat?",
        "Why is my shoulder hurting?",
        "Tell me about progressive overload",
    ]
    
    for input_text in test_inputs:
        prompt_key, scores = router.route(input_text)
        assert prompt_key == "chat_response", f"Failed for input: {input_text}"


def test_route_with_tools_preference():
    """Test routing with tools preference for data references."""
    router = ActionRouter()
    
    # Inputs with data references should prefer tool-using prompts
    input_text = "Based on my 1RM, what should my next program be?"
    prompt_key, scores = router.route_with_tools_preference(input_text)
    
    # Should route to generate_program due to 1RM reference
    assert prompt_key in ["generate_program", "update_routine"]


def test_scoring_fallback():
    """Test scoring fallback when no rules match."""
    router = ActionRouter()
    
    # Generic input with no clear intent
    input_text = "fitness"
    prompt_key, scores = router.route(input_text)
    
    # Should still return a prompt (likely chat_response)
    assert prompt_key in router.available_prompts
    assert isinstance(scores, dict)


def test_route_input_convenience_function():
    """Test the convenience function for routing."""
    prompt_key, scores = route_input("Generate a new program for me")
    
    assert prompt_key == "generate_program"
    assert isinstance(scores, dict)

