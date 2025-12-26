"""
Application settings loaded from environment variables using pydantic-settings.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Google/Gemini API
    GOOGLE_API_KEY: str = Field(..., description="Google API key for Gemini")
    GEMINI_MODEL_ROUTER: str = Field(
        default="gemini-2.5-flash",
        description="Model for routing/planning (cost-effective)",
    )
    GEMINI_MODEL_MAIN: str = Field(
        default="gemini-2.5-pro",
        description="Model for main generation tasks",
    )

    # Prompts
    PROMPTS_DIR: str = Field(
        default="./prompts",
        description="Directory containing prompt YAML files",
    )

    # VM Internal API
    VM_INTERNAL_BASE_URL: str = Field(
        ...,
        description="Base URL for VM internal API (e.g., http://10.0.0.10:8080/internal)",
    )
    VM_INTERNAL_TOKEN: str = Field(
        ...,
        description="Bearer token for VM internal API authentication",
    )

    # Qdrant
    QDRANT_URL: str = Field(..., description="Qdrant server URL")
    QDRANT_API_KEY: Optional[str] = Field(
        default=None,
        description="Qdrant API key (optional)",
    )
    QDRANT_COLLECTION_MEMORY: str = Field(
        default="user_memory",
        description="Qdrant collection name for user memory",
    )

    # OCI
    OCI_STREAM_ID: str = Field(
        ...,
        description="OCI Streaming stream ID for token streaming",
    )
    OCI_RESULT_QUEUE_ID: str = Field(
        ...,
        description="OCI Queue ID for result publishing",
    )

    # Logging
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()

