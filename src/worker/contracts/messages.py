"""
Message contracts for Worker input/output.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    """A single message in conversation history."""

    role: str = Field(..., description="Role: user, assistant, or system")
    content: str = Field(..., description="Message content")


class WorkerRequest(BaseModel):
    """Request payload from the queue."""

    requestId: str = Field(..., description="Unique request identifier for idempotency")
    userId: str = Field(..., description="User identifier")
    conversation_history: List[ConversationMessage] = Field(
        default_factory=list,
        description="Recent conversation history",
    )
    stream: bool = Field(default=True, description="Whether to stream tokens")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata",
    )


class TokenStreamEvent(BaseModel):
    """Event published to token stream."""

    requestId: str = Field(..., description="Request identifier")
    seq: int = Field(..., description="Sequence number")
    delta: str = Field(..., description="Token delta text")
    ts: int = Field(..., description="Unix timestamp in milliseconds")


class ResultStatus(str, Enum):
    """Status of the result."""

    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CLARIFY = "CLARIFY"


class ResultEvent(BaseModel):
    """Event published to result queue."""

    requestId: str = Field(..., description="Request identifier")
    status: ResultStatus = Field(..., description="Result status")
    final: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Final result payload",
    )
    error: Optional[Dict[str, str]] = Field(
        default=None,
        description="Error details if failed",
    )
    usage: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Token usage statistics",
    )
    meta: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadata including intent, action, confidence",
    )

