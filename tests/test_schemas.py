"""Tests for schema validation."""

import pytest
from pydantic import ValidationError

from src.contracts.schemas import (
    ChatPlannerAction,
    ChatPlannerOutput,
    IntentRoutingOutput,
    IntentType,
    ChatResponseOutput,
    GenerateProgramOutput,
    RoutineOutput,
    PlanOutput,
    SetOutput,
)
from src.contracts.messages import RequestPayload, ResultEvent, ResultStatus


class TestIntentRoutingOutput:
    """Tests for IntentRoutingOutput schema."""

    def test_valid_routing_output(self) -> None:
        """Test parsing valid routing output."""
        data = {
            "intent": "CHAT_RESPONSE",
            "confidence": 0.95,
            "required_context": ["active_routines"],
            "needs_clarification": False,
            "clarification_question": "",
        }
        result = IntentRoutingOutput.model_validate(data)
        
        assert result.intent == IntentType.CHAT_RESPONSE
        assert result.confidence == 0.95
        assert result.required_context == ["active_routines"]
        assert result.needs_clarification is False

    def test_routing_with_clarification(self) -> None:
        """Test routing output that needs clarification."""
        data = {
            "intent": "CHAT_RESPONSE",
            "confidence": 0.5,
            "required_context": [],
            "needs_clarification": True,
            "clarification_question": "새 루틴을 만들고 싶으신 건가요?",
        }
        result = IntentRoutingOutput.model_validate(data)
        
        assert result.needs_clarification is True
        assert "루틴" in result.clarification_question

    def test_invalid_intent_rejected(self) -> None:
        """Test that invalid intent values are rejected."""
        data = {
            "intent": "INVALID_INTENT",
            "confidence": 0.9,
            "required_context": [],
            "needs_clarification": False,
            "clarification_question": "",
        }
        with pytest.raises(ValidationError):
            IntentRoutingOutput.model_validate(data)

    def test_confidence_bounds(self) -> None:
        """Test confidence value bounds."""
        # Valid lower bound
        data = {
            "intent": "CHAT_RESPONSE",
            "confidence": 0.0,
            "required_context": [],
            "needs_clarification": False,
            "clarification_question": "",
        }
        result = IntentRoutingOutput.model_validate(data)
        assert result.confidence == 0.0

        # Invalid - below bound
        data["confidence"] = -0.1
        with pytest.raises(ValidationError):
            IntentRoutingOutput.model_validate(data)

        # Invalid - above bound
        data["confidence"] = 1.1
        with pytest.raises(ValidationError):
            IntentRoutingOutput.model_validate(data)


class TestChatPlannerOutput:
    """Tests for ChatPlannerOutput schema."""

    def test_valid_planner_output(self) -> None:
        """Test parsing valid planner output."""
        data = {
            "action": "GET_ACTIVE_ROUTINES",
            "confidence": 0.9,
            "required_context": ["active_routines"],
            "args": {},
            "should_stream": False,
            "needs_clarification": False,
            "clarification_question": "",
            "notes": "User asked about today's workout",
        }
        result = ChatPlannerOutput.model_validate(data)
        
        assert result.action == ChatPlannerAction.GET_ACTIVE_ROUTINES
        assert result.required_context == ["active_routines"]
        assert result.should_stream is False

    def test_planner_with_query_args(self) -> None:
        """Test planner output with query in args."""
        data = {
            "action": "RECALL_USER_MEMORY",
            "confidence": 0.85,
            "required_context": ["user_memory"],
            "args": {"query": "무릎 부상 이력"},
            "should_stream": False,
            "needs_clarification": False,
            "clarification_question": "",
            "notes": "",
        }
        result = ChatPlannerOutput.model_validate(data)
        
        assert result.args.get("query") == "무릎 부상 이력"


class TestChatResponseOutput:
    """Tests for ChatResponseOutput schema."""

    def test_valid_response_output(self) -> None:
        """Test parsing valid chat response."""
        data = {
            "reply": "오늘은 푸쉬데이예요! 벤치프레스부터 시작해볼까요?",
            "suggested_questions": ["세트 구성은 어떻게 되나요?", "오늘 컨디션은 어때요?"],
            "tone": "encouraging",
        }
        result = ChatResponseOutput.model_validate(data)
        
        assert "푸쉬데이" in result.reply
        assert len(result.suggested_questions) == 2

    def test_minimal_response(self) -> None:
        """Test response with only required fields."""
        data = {"reply": "알겠습니다."}
        result = ChatResponseOutput.model_validate(data)
        
        assert result.reply == "알겠습니다."
        assert result.suggested_questions == []


class TestGenerateProgramOutput:
    """Tests for GenerateProgramOutput schema."""

    def test_valid_program_output(self) -> None:
        """Test parsing valid program output."""
        data = {
            "routines": [
                {
                    "routine_name": "Push Day A",
                    "routine_order": 1,
                    "notes": "Focus on chest",
                    "plans": [
                        {
                            "exercise_code": "BARBELL_BENCH_PRESS",
                            "plan_order": 1,
                            "sets": [
                                {"set_type_code": "WARMUP", "set_order": 1, "reps": 10, "weight": 40, "rest_time": 60},
                                {"set_type_code": "NORMAL", "set_order": 2, "reps": 8, "weight": 60, "rest_time": 90},
                            ]
                        }
                    ]
                }
            ]
        }
        result = GenerateProgramOutput.model_validate(data)
        
        assert len(result.routines) == 1
        assert result.routines[0].routine_name == "Push Day A"
        assert len(result.routines[0].plans) == 1
        assert len(result.routines[0].plans[0].sets) == 2


class TestRequestPayload:
    """Tests for RequestPayload schema."""

    def test_valid_request_payload(self) -> None:
        """Test parsing valid request payload."""
        data = {
            "requestId": "550e8400-e29b-41d4-a716-446655440000",
            "userId": "user123",
            "conversationHistory": [
                {"role": "user", "content": "오늘 운동 뭐야?"}
            ],
            "stream": True,
            "metadata": {"source": "mobile"},
        }
        result = RequestPayload.model_validate(data)
        
        assert result.request_id == "550e8400-e29b-41d4-a716-446655440000"
        assert result.user_id == "user123"
        assert len(result.conversation_history) == 1
        assert result.stream is True

    def test_payload_with_snake_case(self) -> None:
        """Test parsing with snake_case field names."""
        data = {
            "request_id": "550e8400-e29b-41d4-a716-446655440000",
            "user_id": "user123",
            "conversation_history": [
                {"role": "assistant", "content": "안녕하세요!"},
                {"role": "user", "content": "루틴 바꿔줘"},
            ],
            "stream": False,
        }
        result = RequestPayload.model_validate(data)
        
        assert result.request_id == "550e8400-e29b-41d4-a716-446655440000"
        assert len(result.conversation_history) == 2


class TestResultEvent:
    """Tests for ResultEvent schema."""

    def test_success_result(self) -> None:
        """Test creating success result."""
        event = ResultEvent(
            request_id="test-123",
            status=ResultStatus.SUCCEEDED,
            final={"reply": "Done!"},
        )
        
        dumped = event.model_dump_json_compat()
        assert dumped["requestId"] == "test-123"
        assert dumped["status"] == "SUCCEEDED"
        assert dumped["final"]["reply"] == "Done!"

    def test_error_result(self) -> None:
        """Test creating error result."""
        event = ResultEvent(
            request_id="test-456",
            status=ResultStatus.FAILED,
            error={"code": "LLM_ERROR", "message": "Model timeout"},
        )
        
        dumped = event.model_dump_json_compat()
        assert dumped["status"] == "FAILED"
        assert dumped["error"]["code"] == "LLM_ERROR"

