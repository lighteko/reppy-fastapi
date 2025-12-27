"""Tests for chat planner context mapping rules."""

import pytest
from src.contracts.schemas import ChatPlannerAction, ChatPlannerOutput


class TestPlannerContextMapping:
    """Tests for planner action to required_context mapping rules."""

    def test_get_active_routines_mapping(self) -> None:
        """GET_ACTIVE_ROUTINES should map to active_routines context."""
        data = {
            "action": "GET_ACTIVE_ROUTINES",
            "confidence": 0.9,
            "required_context": ["active_routines"],
            "args": {},
            "should_stream": False,
            "needs_clarification": False,
            "clarification_question": "",
            "notes": "",
        }
        result = ChatPlannerOutput.model_validate(data)
        
        assert result.action == ChatPlannerAction.GET_ACTIVE_ROUTINES
        assert "active_routines" in result.required_context
        # Should not include other contexts
        assert "user_memory" not in result.required_context
        assert "exercise_catalog" not in result.required_context

    def test_recall_user_memory_mapping(self) -> None:
        """RECALL_USER_MEMORY should map to user_memory context."""
        data = {
            "action": "RECALL_USER_MEMORY",
            "confidence": 0.85,
            "required_context": ["user_memory"],
            "args": {"query": "goal preferences"},
            "should_stream": False,
            "needs_clarification": False,
            "clarification_question": "",
            "notes": "",
        }
        result = ChatPlannerOutput.model_validate(data)
        
        assert result.action == ChatPlannerAction.RECALL_USER_MEMORY
        assert "user_memory" in result.required_context
        assert result.args.get("query") is not None

    def test_find_exercises_mapping(self) -> None:
        """FIND_RELEVANT_EXERCISES should map to exercise_catalog context."""
        data = {
            "action": "FIND_RELEVANT_EXERCISES",
            "confidence": 0.88,
            "required_context": ["exercise_catalog"],
            "args": {"query": "shoulder friendly chest exercises"},
            "should_stream": False,
            "needs_clarification": False,
            "clarification_question": "",
            "notes": "",
        }
        result = ChatPlannerOutput.model_validate(data)
        
        assert result.action == ChatPlannerAction.FIND_RELEVANT_EXERCISES
        assert "exercise_catalog" in result.required_context

    def test_answer_direct_no_context(self) -> None:
        """ANSWER_DIRECT should have empty required_context."""
        data = {
            "action": "ANSWER_DIRECT",
            "confidence": 0.92,
            "required_context": [],
            "args": {},
            "should_stream": True,
            "needs_clarification": False,
            "clarification_question": "",
            "notes": "General nutrition question",
        }
        result = ChatPlannerOutput.model_validate(data)
        
        assert result.action == ChatPlannerAction.ANSWER_DIRECT
        assert result.required_context == []
        assert result.should_stream is True

    def test_ask_clarify_no_context(self) -> None:
        """ASK_CLARIFY should have empty required_context."""
        data = {
            "action": "ASK_CLARIFY",
            "confidence": 0.6,
            "required_context": [],
            "args": {},
            "should_stream": False,
            "needs_clarification": True,
            "clarification_question": "어떤 부위를 말씀하시는 건가요?",
            "notes": "",
        }
        result = ChatPlannerOutput.model_validate(data)
        
        assert result.action == ChatPlannerAction.ASK_CLARIFY
        assert result.required_context == []
        assert result.needs_clarification is True
        assert len(result.clarification_question) > 0

    def test_handoff_no_context(self) -> None:
        """HANDOFF_INTENT_ROUTER should have empty required_context."""
        data = {
            "action": "HANDOFF_INTENT_ROUTER",
            "confidence": 0.5,
            "required_context": [],
            "args": {},
            "should_stream": False,
            "needs_clarification": False,
            "clarification_question": "",
            "notes": "User wants to create new program",
        }
        result = ChatPlannerOutput.model_validate(data)
        
        assert result.action == ChatPlannerAction.HANDOFF_INTENT_ROUTER
        assert result.required_context == []


class TestContextKeyValidation:
    """Tests for context key validation."""

    def test_valid_context_keys(self) -> None:
        """Test all valid context keys are accepted."""
        valid_keys = ["active_routines", "user_memory", "exercise_catalog"]
        
        data = {
            "action": "ANSWER_DIRECT",
            "confidence": 0.9,
            "required_context": valid_keys,
            "args": {},
            "should_stream": False,
            "needs_clarification": False,
            "clarification_question": "",
            "notes": "",
        }
        
        # Should not raise
        result = ChatPlannerOutput.model_validate(data)
        assert set(result.required_context) == set(valid_keys)

    def test_duplicate_context_keys(self) -> None:
        """Test that duplicate keys are preserved (for now)."""
        data = {
            "action": "GET_ACTIVE_ROUTINES",
            "confidence": 0.9,
            "required_context": ["active_routines", "active_routines"],
            "args": {},
            "should_stream": False,
            "needs_clarification": False,
            "clarification_question": "",
            "notes": "",
        }
        
        result = ChatPlannerOutput.model_validate(data)
        # Pydantic preserves duplicates in list
        assert len(result.required_context) == 2

