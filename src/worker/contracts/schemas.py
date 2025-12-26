"""
Pydantic schemas for structured LLM outputs.
These enforce output format from LLM calls.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================
# Intent Routing Schema
# ============================================================


class Intent(str, Enum):
    """Available intents from routing."""

    GENERATE_ROUTINE = "GENERATE_ROUTINE"
    UPDATE_ROUTINE = "UPDATE_ROUTINE"
    CHAT_RESPONSE = "CHAT_RESPONSE"


class IntentRoutingOutput(BaseModel):
    """Output schema for intent routing."""

    intent: Intent = Field(..., description="Which handler should run")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Router confidence in the intent decision",
    )
    required_context: List[str] = Field(
        default_factory=list,
        description="Context keys to fetch before executing the handler",
    )
    needs_clarification: bool = Field(
        default=False,
        description="True if request is ambiguous",
    )
    clarification_question: str = Field(
        default="",
        description="Disambiguating question if needs_clarification is true",
    )


# ============================================================
# Chat Planner Schema
# ============================================================


class PlannerAction(str, Enum):
    """Available actions from chat planner."""

    ANSWER_DIRECT = "ANSWER_DIRECT"
    GET_ACTIVE_ROUTINES = "GET_ACTIVE_ROUTINES"
    RECALL_USER_MEMORY = "RECALL_USER_MEMORY"
    FIND_RELEVANT_EXERCISES = "FIND_RELEVANT_EXERCISES"
    ASK_CLARIFY = "ASK_CLARIFY"
    HANDOFF_INTENT_ROUTER = "HANDOFF_INTENT_ROUTER"


class ChatPlannerOutput(BaseModel):
    """Output schema for chat planner."""

    action: PlannerAction = Field(..., description="Next action for the worker")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Planner confidence for the chosen action",
    )
    required_context: List[str] = Field(
        default_factory=list,
        description="Context keys the worker should fetch",
    )
    args: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments for the chosen action",
    )
    should_stream: bool = Field(
        default=True,
        description="Whether response should be streamed",
    )
    needs_clarification: bool = Field(
        default=False,
        description="True if should ask a clarifying question",
    )
    clarification_question: str = Field(
        default="",
        description="Single short clarifying question",
    )
    notes: str = Field(
        default="",
        description="Short internal note for logs/debugging",
    )


# ============================================================
# Chat Response Schema
# ============================================================


class ChatResponseOutput(BaseModel):
    """Output schema for chat response."""

    reply: str = Field(..., description="Natural-language response to user")
    suggested_questions: Optional[List[str]] = Field(
        default=None,
        description="Optional follow-up questions",
    )
    tone: Optional[str] = Field(
        default=None,
        description="Optional tone descriptor",
    )


# ============================================================
# Generate Program Schema
# ============================================================


class SetSchema(BaseModel):
    """Schema for a single set in a plan."""

    set_type_code: Optional[str] = Field(default=None, description="Set type code")
    set_order: int = Field(..., description="Sequence order of the set")
    reps: Optional[int] = Field(default=None, description="Number of reps")
    weight: Optional[float] = Field(default=None, description="Weight in user's unit")
    rest_time: int = Field(..., description="Rest time in seconds")
    duration: Optional[int] = Field(default=None, description="Duration for timed exercises")


class PlanSchema(BaseModel):
    """Schema for an exercise plan in a routine."""

    exercise_code: str = Field(..., description="Exercise code from available context")
    plan_order: int = Field(..., description="Sequence order of the exercise")
    notes: Optional[str] = Field(default=None, description="Notes for this exercise")
    sets: List[SetSchema] = Field(..., description="Sets for this exercise")


class RoutineSchema(BaseModel):
    """Schema for a single routine."""

    routine_name: str = Field(..., description="Descriptive name for the routine")
    routine_order: int = Field(..., description="Sequence order in the cycle")
    notes: Optional[str] = Field(default=None, description="Overall notes for the routine")
    plans: List[PlanSchema] = Field(..., description="Exercises in this routine")


class GenerateProgramOutput(BaseModel):
    """Output schema for program generation."""

    routines: List[RoutineSchema] = Field(..., description="List of all routines in the program")


# ============================================================
# Update Routine Schema
# ============================================================


class UpdateRoutineOutput(BaseModel):
    """Output schema for routine update (single routine)."""

    routine_name: str = Field(..., description="Name of the routine")
    routine_order: int = Field(..., description="Sequence order")
    notes: Optional[str] = Field(default=None, description="Overall notes")
    plans: List[PlanSchema] = Field(..., description="Updated exercises")


# ============================================================
# Fallback Schemas
# ============================================================


class FallbackIntentRouting(BaseModel):
    """Fallback when intent routing parsing fails."""

    intent: Intent = Intent.CHAT_RESPONSE
    confidence: float = 0.0
    required_context: List[str] = Field(default_factory=list)
    needs_clarification: bool = True
    clarification_question: str = "죄송합니다. 요청을 이해하지 못했어요. 다시 한번 설명해 주시겠어요?"


class FallbackChatPlanner(BaseModel):
    """Fallback when chat planner parsing fails."""

    action: PlannerAction = PlannerAction.ASK_CLARIFY
    confidence: float = 0.0
    required_context: List[str] = Field(default_factory=list)
    args: Dict[str, Any] = Field(default_factory=dict)
    should_stream: bool = False
    needs_clarification: bool = True
    clarification_question: str = "요청을 처리하는 데 문제가 있었어요. 다시 한번 말씀해 주시겠어요?"
    notes: str = "Parsing failed, using fallback"

