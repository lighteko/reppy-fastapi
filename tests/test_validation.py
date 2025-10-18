"""Tests for validation schemas."""

import pytest

from src.common import (
    ChatResponse,
    GenerateProgramResponse,
    UpdateRoutineResponse,
    DomainValidator,
    validate_response,
)


def test_chat_response_validation():
    """Test ChatResponse validation."""
    # Valid data
    data = {
        "reply": "This is a valid reply",
        "suggested_questions": ["Question 1?", "Question 2?"],
        "tone": "encouraging",
    }
    
    response = ChatResponse(**data)
    assert response.reply == "This is a valid reply"
    assert len(response.suggested_questions) == 2


def test_chat_response_empty_reply():
    """Test ChatResponse with empty reply fails."""
    data = {
        "reply": "",
    }
    
    with pytest.raises(ValueError):
        ChatResponse(**data)


def test_generate_program_response_validation():
    """Test GenerateProgramResponse validation."""
    data = {
        "routines": [
            {
                "routine_name": "Push Day A",
                "routine_order": 1,
                "plans": [
                    {
                        "exercise_code": "BARBELL_BENCH_PRESS",
                        "plan_order": 1,
                        "sets": [
                            {
                                "set_type_code": "WARMUP",
                                "set_order": 1,
                                "reps": 10,
                                "weight": 40.0,
                                "rest_time": 60,
                            },
                        ],
                    },
                ],
            },
        ],
    }
    
    response = GenerateProgramResponse(**data)
    assert len(response.routines) == 1
    assert response.routines[0].routine_name == "Push Day A"


def test_domain_validator_exercise_code():
    """Test DomainValidator for exercise codes."""
    available_context = {
        "exercises": [
            {"exercise_code": "BARBELL_BENCH_PRESS"},
            {"exercise_code": "BARBELL_SQUAT"},
        ],
        "set_types": [
            {"set_type_code": "NORMAL"},
            {"set_type_code": "WARMUP"},
        ],
    }
    
    validator = DomainValidator(available_context)
    
    assert validator.validate_exercise_code("BARBELL_BENCH_PRESS") is True
    assert validator.validate_exercise_code("INVALID_CODE") is False


def test_domain_validator_set_type_code():
    """Test DomainValidator for set type codes."""
    available_context = {
        "exercises": [],
        "set_types": [
            {"set_type_code": "NORMAL"},
            {"set_type_code": "WARMUP"},
        ],
    }
    
    validator = DomainValidator(available_context)
    
    assert validator.validate_set_type_code("NORMAL") is True
    assert validator.validate_set_type_code("INVALID_TYPE") is False


def test_validate_routine_with_errors():
    """Test routine validation with errors."""
    available_context = {
        "exercises": [
            {"exercise_code": "BARBELL_BENCH_PRESS"},
        ],
        "set_types": [
            {"set_type_code": "NORMAL"},
        ],
    }
    
    validator = DomainValidator(available_context)
    
    # Routine with invalid exercise code
    routine = {
        "routine_name": "Test Routine",
        "routine_order": 1,
        "plans": [
            {
                "exercise_code": "INVALID_CODE",
                "plan_order": 1,
                "sets": [
                    {
                        "set_type_code": "NORMAL",
                        "set_order": 1,
                        "reps": 10,
                        "rest_time": 60,
                    },
                ],
            },
        ],
    }
    
    result = validator.validate_routine(routine)
    
    assert len(result["errors"]) > 0
    assert any("Invalid exercise code" in err for err in result["errors"])


def test_validate_response_chat():
    """Test validate_response for chat_response."""
    response_data = {
        "reply": "Hello, how can I help you?",
        "suggested_questions": ["What exercises?"],
    }
    
    result = validate_response(
        response_data=response_data,
        prompt_type="chat_response",
    )
    
    assert result["valid"] is True
    assert result["validated_data"] is not None


def test_validate_response_generate_program():
    """Test validate_response for generate_program."""
    response_data = {
        "routines": [
            {
                "routine_name": "Push Day",
                "routine_order": 1,
                "plans": [
                    {
                        "exercise_code": "BARBELL_BENCH_PRESS",
                        "plan_order": 1,
                        "sets": [
                            {
                                "set_order": 1,
                                "reps": 10,
                                "rest_time": 60,
                            },
                        ],
                    },
                ],
            },
        ],
    }
    
    result = validate_response(
        response_data=response_data,
        prompt_type="generate_program",
    )
    
    assert result["valid"] is True

