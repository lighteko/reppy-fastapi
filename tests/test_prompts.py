"""Tests for dynamic prompt loader."""

import pytest
from pathlib import Path

from src.common.prompts import PromptLoader, load_prompt, list_prompts


def test_prompt_loader_discovery():
    """Test that prompt loader discovers YAML files."""
    loader = PromptLoader(prompts_dir="prompts")
    prompts = loader.list_prompts()
    
    assert "chat_response" in prompts
    assert "generate_program" in prompts
    assert "update_routine" in prompts
    assert len(prompts) >= 3


def test_load_chat_response_prompt():
    """Test loading chat_response prompt."""
    prompt_data = load_prompt("chat_response")
    
    assert prompt_data is not None
    assert prompt_data.get("prompt_type") == "chat_response"
    assert "tools" in prompt_data
    assert "variables" in prompt_data
    assert "role" in prompt_data
    assert "instruction" in prompt_data


def test_load_generate_program_prompt():
    """Test loading generate_program prompt."""
    prompt_data = load_prompt("generate_program")
    
    assert prompt_data is not None
    assert prompt_data.get("prompt_type") == "generate_program"
    assert "tools" in prompt_data
    
    # Check for expected tools
    tool_names = [t.get("name") for t in prompt_data["tools"]]
    assert "calculate_one_rep_max" in tool_names
    assert "get_exercise_details" in tool_names
    assert "get_exercise_performance_records" in tool_names


def test_load_update_routine_prompt():
    """Test loading update_routine prompt."""
    prompt_data = load_prompt("update_routine")
    
    assert prompt_data is not None
    assert prompt_data.get("prompt_type") == "update_routine"


def test_load_nonexistent_prompt():
    """Test loading a non-existent prompt raises error."""
    with pytest.raises(FileNotFoundError):
        load_prompt("nonexistent_prompt")


def test_prompt_caching():
    """Test that prompts are cached."""
    loader = PromptLoader(prompts_dir="prompts")
    
    # Load twice
    prompt1 = loader.load_prompt("chat_response")
    prompt2 = loader.load_prompt("chat_response")
    
    # Should be the same object (cached)
    assert prompt1 is prompt2


def test_list_prompts_function():
    """Test convenience function for listing prompts."""
    prompts = list_prompts()
    
    assert isinstance(prompts, list)
    assert len(prompts) >= 3

