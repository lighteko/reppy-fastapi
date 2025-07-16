# /app/rag/retriever.py
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import Qdrant
from qdrant_client import QdrantClient
from app.core.config import settings


def get_retriever():
    """
    Initializes and returns a Qdrant retriever.

    This function sets up the connection to the Qdrant vector store and
    configures it to use OpenAI's embedding model. The retriever is
    responsible for fetching relevant documents based on a query.
    """
    # Initialize OpenAI embeddings
    embeddings = OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL_NAME,
        api_key=settings.OPENAI_API_KEY
    )

    # Initialize Qdrant client
    client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
    )

    # Initialize the Qdrant vector store wrapper
    qdrant_store = Qdrant(
        client=client,
        collection_name=settings.QDRANT_COLLECTION_NAME,
        embeddings=embeddings,
    )

    # Convert the vector store into a retriever instance
    # `k=4` specifies that it should retrieve the top 4 most relevant documents.
    return qdrant_store.as_retriever(search_kwargs={"k": 4})
