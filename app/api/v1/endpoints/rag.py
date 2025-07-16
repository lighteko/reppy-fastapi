from fastapi import APIRouter, Depends, HTTPException, Request
from langchain_core.runnables import Runnable
from sse_starlette.sse import EventSourceResponse
import json

from app.rag.schemas import RAGRequest, RAGResponse

# Create a new router for RAG endpoints
router = APIRouter()


def get_rag_chain(request: Request) -> Runnable:
    """
    Dependency function to get the RAG chain from the application state.
    This makes the chain, which was initialized on startup, accessible to the endpoint.
    """
    rag_chain = request.app.state.rag_chain
    if not rag_chain:
        raise HTTPException(
            status_code=503,
            detail="RAG chain is not available. The server may be initializing or has encountered an error."
        )
    return rag_chain


@router.post("/chat", response_model=RAGResponse)
async def rag_chat_endpoint(
        request: RAGRequest,
        rag_chain: Runnable = Depends(get_rag_chain)
):
    """
    Endpoint to interact with the RAG chain.
    It takes a user's question and returns a generated answer along with the source documents.
    This is a standard, non-streaming invocation.
    """
    try:
        # The invoke method runs the entire chain and waits for the final result.
        result = rag_chain.invoke(request.question)

        # The result from our custom chain includes 'answer' and 'docs'.
        # FastAPI's response model automatically handles serialization of Document objects here.
        return RAGResponse(answer=result['answer'], sources=result['docs'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@router.post("/chat/stream")
async def rag_chat_streaming_endpoint(
        request: RAGRequest,
        rag_chain: Runnable = Depends(get_rag_chain)
):
    """
    Endpoint for streaming the RAG chain's response using Server-Sent Events (SSE).
    This provides a real-time, token-by-token response to the client.
    """

    async def event_generator():
        try:
            # The astream() method streams chunks from the chain as they are generated.
            async for chunk in rag_chain.astream(request.question):
                # *** FIX APPLIED HERE ***
                # Check if the chunk contains the 'docs' key.
                if "docs" in chunk:
                    # LangChain's Document object is a Pydantic model. We must convert it
                    # to a dictionary to make it JSON serializable with json.dumps().
                    # .model_dump() is the Pydantic v2 method for this.
                    chunk["docs"] = [doc.model_dump() for doc in chunk["docs"]]

                # Ensure there's content before yielding
                if chunk:
                    yield json.dumps(chunk)
        except Exception as e:
            # Handle potential errors during the streaming process.
            error_message = {"error": f"An error occurred during streaming: {str(e)}"}
            yield json.dumps(error_message)

    return EventSourceResponse(event_generator())
