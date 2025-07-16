# /app/core/config.py
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()


class Settings(BaseSettings):
    """
    Pydantic settings class to manage application configuration and secrets.
    It automatically reads environment variables.
    """
    PROJECT_NAME: str = "LangChain RAG API Server"
    API_V1_STR: str = "/api/v1"

    # OpenAI API Key
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Qdrant Configuration
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY: str | None = os.getenv("QDRANT_API_KEY")
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "my_collection")

    # Embedding model configuration
    EMBEDDING_MODEL_NAME: str = "text-embedding-3-small"

    # LLM configuration
    LLM_MODEL_NAME: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.1

    class Config:
        # This allows the settings to be loaded from a .env file
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create a single instance of the settings to be used throughout the application
settings = Settings()
