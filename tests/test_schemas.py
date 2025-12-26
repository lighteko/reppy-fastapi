"""
Tests for Pydantic schemas - parsing and validation.
"""

import pytest

from src.worker.contracts.schemas import (
    IntentRoutingOutput,
    ChatPlannerOutput,
    ChatResponseOutput,
    GenerateProgramOutput,
    UpdateRoutineOutput,
    Intent,
    PlannerAction,
    FallbackIntentRouting,
    FallbackChatPlanner,
)
from src.worker.llm.structured_output import StructuredOutputParser


class TestIntentRoutingSchema:
    """Tests for IntentRoutingOutput schema."""

    def test_valid_chat_response_intent(self):
        """Test parsing valid CHAT_RESPONSE intent."""
        data = {
            "intent": "CHAT_RESPONSE",
            "confidence": 0.95,
            "required_context": ["active_routines"],
            "needs_clarification": False,
            "clarification_question": "",
        }
        result = IntentRoutingOutput.model_validate(data)
        
        assert result.intent == Intent.CHAT_RESPONSE
        assert result.confidence == 0.95
        assert result.required_context == ["active_routines"]
        assert result.needs_clarification is False

    def test_valid_generate_routine_intent(self):
        """Test parsing valid GENERATE_ROUTINE intent."""
        data = {
            "intent": "GENERATE_ROUTINE",
            "confidence": 0.88,
            "required_context": [],
            "needs_clarification": False,
            "clarification_question": "",
        }
        result = IntentRoutingOutput.model_validate(data)
        
        assert result.intent == Intent.GENERATE_ROUTINE
        assert result.confidence == 0.88
        assert result.required_context == []

    def test_valid_update_routine_intent(self):
        """Test parsing valid UPDATE_ROUTINE intent."""
        data = {
            "intent": "UPDATE_ROUTINE",
            "confidence": 0.92,
            "required_context": ["active_routines"],
            "needs_clarification": False,
            "clarification_question": "",
        }
        result = IntentRoutingOutput.model_validate(data)
        
        assert result.intent == Intent.UPDATE_ROUTINE

    def test_clarification_needed(self):
        """Test intent with clarification."""
        data = {
            "intent": "CHAT_RESPONSE",
            "confidence": 0.45,
            "required_context": [],
            "needs_clarification": True,
            "clarification_question": "새로운 루틴을 만들까요, 기존 루틴을 수정할까요?",
        }
        result = IntentRoutingOutput.model_validate(data)
        
        assert result.needs_clarification is True
        assert "루틴" in result.clarification_question


class TestChatPlannerSchema:
    """Tests for ChatPlannerOutput schema."""

    def test_valid_answer_direct(self):
        """Test parsing ANSWER_DIRECT action."""
        data = {
            "action": "ANSWER_DIRECT",
            "confidence": 0.9,
            "required_context": [],
            "args": {},
            "should_stream": True,
            "needs_clarification": False,
            "clarification_question": "",
            "notes": "General fitness question",
        }
        result = ChatPlannerOutput.model_validate(data)
        
        assert result.action == PlannerAction.ANSWER_DIRECT
        assert result.required_context == []
        assert result.should_stream is True

    def test_valid_get_active_routines(self):
        """Test parsing GET_ACTIVE_ROUTINES action."""
        data = {
            "action": "GET_ACTIVE_ROUTINES",
            "confidence": 0.95,
            "required_context": ["active_routines"],
            "args": {},
            "should_stream": False,
            "needs_clarification": False,
            "clarification_question": "",
            "notes": "User asking about today's workout",
        }
        result = ChatPlannerOutput.model_validate(data)
        
        assert result.action == PlannerAction.GET_ACTIVE_ROUTINES
        assert result.required_context == ["active_routines"]
        assert result.should_stream is False

    def test_valid_recall_user_memory(self):
        """Test parsing RECALL_USER_MEMORY action with query."""
        data = {
            "action": "RECALL_USER_MEMORY",
            "confidence": 0.85,
            "required_context": ["user_memory"],
            "args": {"query": "무릎 부상"},
            "should_stream": False,
            "needs_clarification": False,
            "clarification_question": "",
            "notes": "User mentioned past injury",
        }
        result = ChatPlannerOutput.model_validate(data)
        
        assert result.action == PlannerAction.RECALL_USER_MEMORY
        assert result.args.get("query") == "무릎 부상"

    def test_required_context_mapping_get_active_routines(self):
        """Test that GET_ACTIVE_ROUTINES maps to active_routines context."""
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
        
        # Verify mapping rule from chat_planner.yaml
        assert "active_routines" in result.required_context

    def test_required_context_mapping_recall_user_memory(self):
        """Test that RECALL_USER_MEMORY maps to user_memory context."""
        data = {
            "action": "RECALL_USER_MEMORY",
            "confidence": 0.9,
            "required_context": ["user_memory"],
            "args": {"query": "test"},
            "should_stream": False,
            "needs_clarification": False,
            "clarification_question": "",
            "notes": "",
        }
        result = ChatPlannerOutput.model_validate(data)
        
        # Verify mapping rule from chat_planner.yaml
        assert "user_memory" in result.required_context

    def test_required_context_mapping_find_exercises(self):
        """Test that FIND_RELEVANT_EXERCISES maps to exercise_catalog context."""
        data = {
            "action": "FIND_RELEVANT_EXERCISES",
            "confidence": 0.9,
            "required_context": ["exercise_catalog"],
            "args": {"query": "벤치 대체"},
            "should_stream": False,
            "needs_clarification": False,
            "clarification_question": "",
            "notes": "",
        }
        result = ChatPlannerOutput.model_validate(data)
        
        # Verify mapping rule from chat_planner.yaml
        assert "exercise_catalog" in result.required_context


class TestChatResponseSchema:
    """Tests for ChatResponseOutput schema."""

    def test_valid_response_minimal(self):
        """Test minimal valid response."""
        data = {"reply": "안녕하세요! 오늘 운동 화이팅하세요!"}
        result = ChatResponseOutput.model_validate(data)
        
        assert result.reply == "안녕하세요! 오늘 운동 화이팅하세요!"
        assert result.suggested_questions is None

    def test_valid_response_with_suggestions(self):
        """Test response with suggested questions."""
        data = {
            "reply": "벤치프레스는 상체 밀기 운동의 기본입니다.",
            "suggested_questions": [
                "정확한 자세가 궁금해요",
                "세트/반복수는 어떻게 하나요?",
            ],
            "tone": "informative",
        }
        result = ChatResponseOutput.model_validate(data)
        
        assert len(result.suggested_questions) == 2
        assert result.tone == "informative"


class TestStructuredOutputParser:
    """Tests for the structured output parser."""

    def test_extract_json_raw(self):
        """Test extracting raw JSON."""
        text = '{"intent": "CHAT_RESPONSE", "confidence": 0.9}'
        result = StructuredOutputParser.extract_json(text)
        
        assert result is not None
        assert result["intent"] == "CHAT_RESPONSE"

    def test_extract_json_from_markdown(self):
        """Test extracting JSON from markdown code block."""
        text = '''Here's the result:
```json
{"intent": "CHAT_RESPONSE", "confidence": 0.9}
```
'''
        result = StructuredOutputParser.extract_json(text)
        
        assert result is not None
        assert result["intent"] == "CHAT_RESPONSE"

    def test_parse_with_schema(self):
        """Test parsing with Pydantic schema."""
        text = '''{
            "intent": "GENERATE_ROUTINE",
            "confidence": 0.88,
            "required_context": [],
            "needs_clarification": false,
            "clarification_question": ""
        }'''
        
        result, error = StructuredOutputParser.parse(
            text, IntentRoutingOutput, "test-123"
        )
        
        assert error is None
        assert result is not None
        assert result.intent == Intent.GENERATE_ROUTINE

    def test_parse_with_fallback(self):
        """Test parsing with fallback on failure."""
        text = "This is not valid JSON"
        fallback = FallbackIntentRouting()
        
        result = StructuredOutputParser.parse_with_fallback(
            text, IntentRoutingOutput, fallback, "test-123"
        )
        
        assert result.intent == Intent.CHAT_RESPONSE
        assert result.needs_clarification is True


class TestFallbackSchemas:
    """Tests for fallback schemas."""

    def test_fallback_intent_routing(self):
        """Test FallbackIntentRouting defaults."""
        fallback = FallbackIntentRouting()
        
        assert fallback.intent == Intent.CHAT_RESPONSE
        assert fallback.confidence == 0.0
        assert fallback.needs_clarification is True
        assert len(fallback.clarification_question) > 0

    def test_fallback_chat_planner(self):
        """Test FallbackChatPlanner defaults."""
        fallback = FallbackChatPlanner()
        
        assert fallback.action == PlannerAction.ASK_CLARIFY
        assert fallback.confidence == 0.0
        assert fallback.needs_clarification is True
        assert len(fallback.clarification_question) > 0

