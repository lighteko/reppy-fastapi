"""Application settings using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Google/Gemini
    google_api_key: str = Field(..., description="Google API key for Gemini")
    gemini_model_router: str = Field(
        default="gemini-2.0-flash",
        description="Gemini model for routing/planning (fast, cheap)",
    )
    gemini_model_main: str = Field(
        default="gemini-2.5-pro-preview-06-05",
        description="Gemini model for main generation (powerful)",
    )

    # Prompts
    prompts_dir: str = Field(
        default="./prompts",
        description="Directory containing prompt YAML files",
    )

    # VM Internal API
    vm_internal_base_url: str = Field(
        ...,
        description="Base URL for VM internal API (e.g., http://10.0.0.10:8080/internal)",
    )
    vm_internal_token: str = Field(
        ...,
        description="Bearer token for VM internal API authentication",
    )

    # Qdrant
    qdrant_url: str = Field(..., description="Qdrant server URL")
    qdrant_api_key: str | None = Field(
        default=None,
        description="Qdrant API key (optional)",
    )
    qdrant_collection_memory: str = Field(
        default="user_memory",
        description="Qdrant collection name for user memory",
    )

    # OCI
    oci_stream_id: str = Field(..., description="OCI Streaming stream OCID for token streaming")
    oci_result_queue_id: str = Field(..., description="OCI Queue OCID for result publishing")
    oci_config_profile: str = Field(
        default="DEFAULT",
        description="OCI config profile name",
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    # Timeouts
    http_timeout_seconds: float = Field(
        default=30.0,
        description="HTTP client timeout in seconds",
    )
    llm_timeout_seconds: float = Field(
        default=120.0,
        description="LLM call timeout in seconds",
    )

    @field_validator("vm_internal_base_url")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        """Remove trailing slash from base URL."""
        return v.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()  # type: ignore[call-arg]

