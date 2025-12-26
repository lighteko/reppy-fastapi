"""Singleton configuration loader from environment variables."""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # LLM Settings
    llm_provider: str = Field(default="openai", description="LLM provider (openai, anthropic, etc.)")
    llm_model: str = Field(default="gpt-4-turbo-preview", description="LLM model name for tool calling")
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="LLM temperature")
    llm_max_tokens: int = Field(default=4096, ge=1, description="Maximum tokens for LLM response")
    openai_api_key: str = Field(default="", description="OpenAI API key")
    
    # Router LLM Settings (lightweight model for intent classification)
    router_llm_model: str = Field(default="gpt-4o-mini", description="Lightweight model for action routing")
    
    # Embedding Settings
    embedding_model: str = Field(default="text-embedding-3-small", description="Embedding model name")
    embedding_dimension: int = Field(default=1536, description="Embedding vector dimension")
    
    # Qdrant Settings
    qdrant_backend: str = Field(default="qdrant", description="Vector DB backend")
    qdrant_url: str = Field(default="http://localhost:6333", description="Qdrant server URL")
    qdrant_api_key: Optional[str] = Field(default=None, description="Qdrant API key")
    qdrant_grpc: bool = Field(default=False, description="Use gRPC for Qdrant")
    qdrant_exercises_collection: str = Field(default="exercises", description="Qdrant exercises collection name")
    qdrant_memory_collection: str = Field(default="user_memory", description="Qdrant user memory collection name")
    qdrant_vector_size: int = Field(default=1536, description="Vector size")
    qdrant_distance: str = Field(default="Cosine", description="Distance metric")
    qdrant_search_k: int = Field(default=5, ge=1, description="Number of results to retrieve")
    qdrant_use_mmr: bool = Field(default=True, description="Use MMR for diversity")
    qdrant_mmr_lambda: float = Field(default=0.5, ge=0.0, le=1.0, description="MMR lambda parameter")
    qdrant_use_rerank: bool = Field(default=False, description="Use reranking")
    
    # Express Server Settings
    express_base_url: str = Field(default="http://localhost:3000", description="Express API base URL")
    express_api_key: Optional[str] = Field(default=None, description="Express API key for auth")
    express_timeout: int = Field(default=30, ge=1, description="Express API timeout in seconds")
    express_max_retries: int = Field(default=3, ge=0, description="Max retries for Express API")
    express_retry_backoff: float = Field(default=1.0, ge=0.1, description="Retry backoff factor")
    
    # Agent Executor Settings
    agent_max_iterations: int = Field(default=8, ge=1, le=20, description="Max agent iterations")
    agent_parsing_retries: int = Field(default=2, ge=0, description="Parsing retry attempts")
    tool_timeout: int = Field(default=30, ge=1, description="Tool execution timeout in seconds")
    llm_timeout: int = Field(default=60, ge=1, description="LLM timeout in seconds")
    
    # Prompt Settings
    prompts_directory: str = Field(default="prompts", description="Directory containing prompt YAML files")
    
    # Plate Rounding & Locale
    plate_rounding_increment: float = Field(default=2.5, description="Weight rounding increment")
    default_locale: str = Field(default="en-US", description="Default locale")
    
    # Logging & Observability
    log_level: str = Field(default="INFO", description="Logging level")
    enable_langsmith: bool = Field(default=False, description="Enable LangSmith tracing")
    langsmith_api_key: Optional[str] = Field(default=None, description="LangSmith API key")
    langsmith_project: Optional[str] = Field(default="reppy-rag", description="LangSmith project name")
    
    # OCI Authentication Settings
    oci_region: str = Field(default="us-ashburn-1", description="OCI region")
    oci_tenancy_ocid: Optional[str] = Field(default=None, description="OCI tenancy OCID")
    oci_user_ocid: Optional[str] = Field(default=None, description="OCI user OCID")
    oci_fingerprint: Optional[str] = Field(default=None, description="OCI API key fingerprint")
    oci_private_key_path: Optional[str] = Field(default=None, description="OCI API private key path")
    oci_private_key_passphrase: Optional[str] = Field(default=None, description="OCI API key passphrase")

    # OCI Resource Principal Settings (Functions/Cloud Shell/Compute)
    oci_resource_principal_version: Optional[str] = Field(
        default=None,
        description="OCI resource principal version (e.g., 2.2)"
    )
    oci_resource_principal_region: Optional[str] = Field(
        default=None,
        description="OCI resource principal region"
    )
    oci_resource_principal_rpst: Optional[str] = Field(
        default=None,
        description="OCI resource principal RPST"
    )
    oci_resource_principal_private_pem: Optional[str] = Field(
        default=None,
        description="OCI resource principal private PEM"
    )

    # OCI Functions Settings
    oci_functions_endpoint: Optional[str] = Field(default=None, description="OCI Functions endpoint URL")
    oci_functions_application_ocid: Optional[str] = Field(
        default=None,
        description="OCI Functions application OCID"
    )

    # OCIR Settings
    ocir_registry: Optional[str] = Field(default=None, description="OCIR registry hostname")
    ocir_namespace: Optional[str] = Field(default=None, description="OCIR namespace")
    ocir_repository: Optional[str] = Field(default=None, description="OCIR repository name")
    ocir_username: Optional[str] = Field(default=None, description="OCIR username")
    ocir_password: Optional[str] = Field(default=None, description="OCIR auth token/password")

    # OCI Queue Settings
    oci_queue_ocid: Optional[str] = Field(default=None, description="OCI Queue OCID")
    oci_queue_endpoint: Optional[str] = Field(default=None, description="OCI Queue endpoint URL")


# Singleton instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the singleton configuration instance.
    
    Returns:
        Config: The application configuration instance.
    """
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config() -> Config:
    """Force reload the configuration (mainly for testing).
    
    Returns:
        Config: The newly loaded configuration instance.
    """
    global _config
    _config = Config()
    return _config
