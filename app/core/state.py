# /app/core/state.py
from pydantic import BaseModel
from langchain_core.language_models import BaseChatModel

class AppState(BaseModel):
    """
    A Pydantic model to define the structure of the application's state,
    providing type hints for the different AI models used by the app.
    """
    models: dict[str, BaseChatModel] = {}

    class Config:
        # Pydantic needs this to allow complex, non-standard types
        # like the LangChain model objects.
        arbitrary_types_allowed = True
