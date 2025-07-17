# /app/core/config.py
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

class Settings(BaseSettings):
    """
    Pydantic settings class to manage application configuration for the Reppy AI server.
    """
    PROJECT_NAME: str = "Reppy AI Server"
    API_V1_STR: str = "/api/v1"

    # OpenAI API Key
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # --- Model Configuration ---
    # A powerful model for generating structured workout routines.
    ROUTINE_GENERATOR_LLM: str = "gpt-4o"
    # A fast, conversational model for the interactive AI coach.
    COACH_LLM: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.7 # Higher temperature for more creative/varied routines

    # --- Qdrant Configuration (Re-added for future use) ---
    QDRANT_URL: str | None = os.getenv("QDRANT_URL")
    QDRANT_API_KEY: str | None = os.getenv("QDRANT_API_KEY")


    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

# Create a single instance of the settings to be used throughout the application
settings = Settings()
