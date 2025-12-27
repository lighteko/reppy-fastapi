"""Pydantic schemas for LLM structured outputs."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Intent Routing
# =============================================================================


class IntentType(str, Enum):
    """Valid intent types for routing."""

    GENERATE_ROUTINE = "GENERATE_ROUTINE"
    UPDATE_ROUTINE = "UPDATE_ROUTINE"
    CHAT_RESPONSE = "CHAT_RESPONSE"


class ContextKey(str, Enum):
    """Valid context keys for fetching."""

    ACTIVE_ROUTINES = "active_routines"
    USER_MEMORY = "user_memory"
    EXERCISE_CATALOG = "exercise_catalog"


class IntentRoutingOutput(BaseModel):
    """Output schema for intent routing LLM call."""

    intent: IntentType = Field(..., description="Which handler should run.")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Router confidence in the intent decision.",
    )
    required_context: list[str] = Field(
        default_factory=list,
        description="Context keys to fetch before executing the chosen handler.",
    )
    needs_clarification: bool = Field(
        default=False,
        description="True if the request is ambiguous.",
    )
    clarification_question: str = Field(
        default="",
        description="A single short disambiguating question.",
    )


# =============================================================================
# Chat Planner
# =============================================================================


class ChatPlannerAction(str, Enum):
    """Valid actions for the chat planner."""

    ANSWER_DIRECT = "ANSWER_DIRECT"
    GET_ACTIVE_ROUTINES = "GET_ACTIVE_ROUTINES"
    RECALL_USER_MEMORY = "RECALL_USER_MEMORY"
    FIND_RELEVANT_EXERCISES = "FIND_RELEVANT_EXERCISES"
    ASK_CLARIFY = "ASK_CLARIFY"
    HANDOFF_INTENT_ROUTER = "HANDOFF_INTENT_ROUTER"


class ChatPlannerOutput(BaseModel):
    """Output schema for chat planner LLM call."""

    action: ChatPlannerAction = Field(..., description="Next action for the worker.")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Planner confidence for the chosen action.",
    )
    required_context: list[str] = Field(
        default_factory=list,
        description="Context keys the worker should fetch.",
    )
    args: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments for the chosen action.",
    )
    should_stream: bool = Field(
        default=False,
        description="Whether the response should be streamed.",
    )
    needs_clarification: bool = Field(
        default=False,
        description="True if a clarifying question should be asked.",
    )
    clarification_question: str = Field(
        default="",
        description="Single short question for clarification.",
    )
    notes: str = Field(
        default="",
        description="Short internal note for logs/debugging.",
    )


# =============================================================================
# Chat Response
# =============================================================================


class ChatResponseOutput(BaseModel):
    """Output schema for chat response LLM call."""

    reply: str = Field(..., description="Natural language response to the user.")
    suggested_questions: list[str] = Field(
        default_factory=list,
        description="Optional follow-up questions.",
    )
    tone: str = Field(
        default="",
        description="Optional tone descriptor.",
    )


# =============================================================================
# Generate Program
# =============================================================================


class SetOutput(BaseModel):
    """Single set in an exercise plan."""

    set_type_code: str | None = Field(default=None, description="Set type code.")
    set_order: int = Field(..., description="Sequence order of the set.")
    reps: int | None = Field(default=None, description="Number of reps.")
    weight: float | None = Field(default=None, description="Weight in user's unit system.")
    rest_time: int = Field(..., description="Rest time in seconds.")
    duration: int | None = Field(default=None, description="Duration in seconds for timed exercises.")


class PlanOutput(BaseModel):
    """Single exercise plan within a routine."""

    exercise_code: str = Field(..., description="Exercise code from available context.")
    plan_order: int = Field(..., description="Sequence order in the routine.")
    notes: str | None = Field(default=None, description="Optional notes.")
    sets: list[SetOutput] = Field(..., description="Sets for this exercise.")


class RoutineOutput(BaseModel):
    """Single routine in a program."""

    routine_name: str = Field(..., description="Name of the routine.")
    routine_order: int = Field(..., description="Sequence order in the cycle.")
    notes: str | None = Field(default=None, description="Optional notes.")
    plans: list[PlanOutput] = Field(..., description="Exercises in this routine.")


class GenerateProgramOutput(BaseModel):
    """Output schema for program generation LLM call."""

    routines: list[RoutineOutput] = Field(..., description="List of routines in the program.")


# =============================================================================
# Update Routine
# =============================================================================


class UpdateRoutineOutput(BaseModel):
    """Output schema for routine update LLM call.
    
    Same structure as RoutineOutput but represents a modified routine.
    """

    routine_name: str = Field(..., description="Name of the routine.")
    routine_order: int = Field(..., description="Sequence order in the cycle.")
    notes: str | None = Field(default=None, description="Optional notes explaining changes.")
    plans: list[PlanOutput] = Field(..., description="Updated exercises in this routine.")

