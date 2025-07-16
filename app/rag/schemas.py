# /app/rag/schemas.py
from pydantic import BaseModel, Field
from langchain_core.documents import Document

class RAGRequest(BaseModel):
    """
    Pydantic model for the incoming request to the RAG endpoint.
    """
    question: str = Field(
        ...,
        description="The question to be answered by the RAG chain.",
        examples=["What is the capital of France?"]
    )

class RAGResponse(BaseModel):
    """
    Pydantic model for the response from the RAG endpoint.
    """
    answer: str = Field(
        ...,
        description="The generated answer from the RAG chain."
    )
    sources: list[Document] = Field(
        ...,
        description="A list of source documents used to generate the answer."
    )

class RAGStreamingResponse(BaseModel):
    """
    Pydantic model for each chunk in a streaming response.
    """
    answer_chunk: str | None = None
    docs_chunk: list[Document] | None = None
