"""Message contracts for Worker input/output."""

import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Input Messages
# =============================================================================


class ConversationMessage(BaseModel):
    """Single message in conversation history."""

    role: str = Field(..., description="Message role: user, assistant, or system.")
    content: str = Field(..., description="Message content.")


class RequestPayload(BaseModel):
    """Request payload from request-queue."""

    request_id: str = Field(..., alias="requestId", description="Unique request identifier.")
    user_id: str = Field(..., alias="userId", description="User identifier.")
    conversation_history: list[ConversationMessage] = Field(
        ...,
        alias="conversationHistory",
        description="Recent conversation history.",
    )
    stream: bool = Field(default=True, description="Whether to stream tokens.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata.",
    )

    class Config:
        populate_by_name = True


# =============================================================================
# Output Messages
# =============================================================================


class TokenStreamEvent(BaseModel):
    """Token streaming event for OCI Streaming."""

    request_id: str = Field(..., alias="requestId")
    seq: int = Field(..., description="Sequence number of this token.")
    delta: str = Field(..., description="Token text.")
    ts: int = Field(default_factory=lambda: int(time.time() * 1000), description="Timestamp in ms.")

    class Config:
        populate_by_name = True

    def model_dump_json_compat(self) -> dict[str, Any]:
        """Return dict with camelCase keys for JSON serialization."""
        return {
            "requestId": self.request_id,
            "seq": self.seq,
            "delta": self.delta,
            "ts": self.ts,
        }


class ResultStatus(str, Enum):
    """Result status types."""

    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CLARIFY = "CLARIFY"


class UsageInfo(BaseModel):
    """Token usage information."""

    prompt_tokens: int = Field(default=0, alias="promptTokens")
    completion_tokens: int = Field(default=0, alias="completionTokens")
    total_tokens: int = Field(default=0, alias="totalTokens")

    class Config:
        populate_by_name = True


class ResultMeta(BaseModel):
    """Result metadata."""

    intent: str = Field(default="", description="Detected intent.")
    action: str = Field(default="", description="Executed action.")
    confidence: float = Field(default=0.0, description="Confidence score.")


class ResultEvent(BaseModel):
    """Final result event for result-queue."""

    request_id: str = Field(..., alias="requestId")
    status: ResultStatus = Field(..., description="Result status.")
    final: dict[str, Any] = Field(default_factory=dict, description="Final result data.")
    error: dict[str, str] | None = Field(default=None, description="Error info if failed.")
    usage: UsageInfo | None = Field(default=None, description="Token usage.")
    meta: ResultMeta = Field(default_factory=ResultMeta, description="Metadata.")

    class Config:
        populate_by_name = True

    def model_dump_json_compat(self) -> dict[str, Any]:
        """Return dict with camelCase keys for JSON serialization."""
        result: dict[str, Any] = {
            "requestId": self.request_id,
            "status": self.status.value,
            "final": self.final,
            "error": self.error,
            "meta": {
                "intent": self.meta.intent,
                "action": self.meta.action,
                "confidence": self.meta.confidence,
            },
        }
        if self.usage:
            result["usage"] = {
                "promptTokens": self.usage.prompt_tokens,
                "completionTokens": self.usage.completion_tokens,
                "totalTokens": self.usage.total_tokens,
            }
        return result

