# /app/rag/llm.py
from langchain_openai import ChatOpenAI
from app.core.config import settings


def get_llm():
    """
    Initializes and returns the language model for the RAG chain.

    This function configures the ChatOpenAI model with the specified parameters
    from the application settings, such as the model name and temperature.
    """
    llm = ChatOpenAI(
        model=settings.LLM_MODEL_NAME,
        temperature=settings.LLM_TEMPERATURE,
        api_key=settings.OPENAI_API_KEY
    )
    return llm
