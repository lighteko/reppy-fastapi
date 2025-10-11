"""Pydantic data models shared across the service."""

from __future__ import annotations

from typing import Any, Iterable, Literal, Optional

from pydantic import BaseModel, Field, validator


class ChatMessage(BaseModel):
    """A single message exchanged between the user and assistant."""

    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Request payload for the streaming chat endpoint."""

    user_id: str = Field(..., description="Identifier for the user sending the chat message.")
    messages: list[ChatMessage] = Field(..., min_items=1)
    top_k: int = Field(5, ge=1, le=20, description="How many memories to retrieve from the vector store.")

    @property
    def latest_user_message(self) -> Optional[str]:
        for message in reversed(self.messages):
            if message.role == "user":
                return message.content
        return None


class PromptConfig(BaseModel):
    """Inner prompt configuration as stored inside YAML files."""

    prompt_type: str
    tools: list[str] = Field(default_factory=list)
    variables: list[str] = Field(default_factory=list)
    role: str
    instruction: str
    response_type: str = Field(default="JSON")
    response_schema: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class PromptTemplate(BaseModel):
    """Serializable representation of a structured prompt template."""

    version: str
    prompt: PromptConfig

    def required_variables(self) -> set[str]:
        return set(self.prompt.variables)


class RoutineSet(BaseModel):
    """One set within a workout plan."""

    set_type_name: Optional[str] = Field(
        None, description="Human readable label for the set prescription (e.g. Warm-up, Drop Set)."
    )
    set_order: int = Field(..., ge=0)
    reps: Optional[int] = Field(None, ge=0)
    weight: Optional[float]
    rest_time: int = Field(..., ge=0)
    duration: Optional[int] = Field(None, ge=0)


class RoutinePlan(BaseModel):
    """A plan for a single exercise within a routine."""

    exercise_name: str = Field(..., description="Name of the exercise as presented to the model.")
    plan_order: int = Field(..., ge=0)
    notes: Optional[str] = None
    sets: list[RoutineSet] = Field(..., min_items=1)


class Routine(BaseModel):
    """A single scheduled routine in a program."""

    routine_name: str
    routine_order: int = Field(..., ge=0)
    notes: Optional[str] = None
    plans: list[RoutinePlan] = Field(..., min_items=1)


class RoutineBatch(BaseModel):
    """Envelope containing all generated routines for persistence."""

    program_name: Optional[str] = None
    start_date: Optional[str] = None
    goal_date: Optional[str] = None
    goal: Optional[str] = None
    routines: list[Routine] = Field(..., min_items=1)


class GenerateProgramJob(BaseModel):
    """Payload describing the asynchronous generate_program job."""

    job_type: str = Field("generate_program", const=True)
    user_id: str
    program_id: Optional[str] = None
    program_name: Optional[str] = None
    goal: Optional[str] = None
    user_context: Optional[str] = None
    top_k: int = Field(10, ge=1, le=50)
    qdrant_collection: Optional[str] = Field(None, description="Override Qdrant collection name if provided.")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @validator("metadata", pre=True)
    def _default_metadata(cls, value: Any) -> dict[str, Any]:
        return value or {}

    def build_query_text(self) -> str:
        """Create a textual query for embeddings based on provided context."""

        segments: list[str] = []
        if self.goal:
            segments.append(f"Goal: {self.goal}")
        if self.user_context:
            segments.append(self.user_context)
        if self.program_name:
            segments.append(f"Program Name: {self.program_name}")
        if not segments:
            segments.append(f"User {self.user_id} fitness preferences")
        return "\n".join(segments)

    def prompt_context(self) -> dict[str, Any]:
        """Build a structured prompt context to pass into templates."""

        return {
            "program_name": self.program_name,
            "goal": self.goal,
            "user_context": self.user_context,
            "metadata": self.metadata,
        }


def ensure_required_variables(template: PromptTemplate, provided: Iterable[str]) -> None:
    """Validate that all required prompt variables are present."""

    missing = template.required_variables() - set(provided)
    if missing:
        raise ValueError(f"Missing prompt variables: {', '.join(sorted(missing))}")

