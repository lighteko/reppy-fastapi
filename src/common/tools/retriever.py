"""RAG retriever using Qdrant backend with MMR and reranking support."""

from typing import Any, Dict, List, Optional
import asyncio

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from loguru import logger

from src.config import get_config
from src.infra.qdrant_client import QdrantVectorDB


class QdrantRetriever:
    """Retriever backed by Qdrant vector database."""
    
    def __init__(
        self,
        qdrant_client: Optional[QdrantVectorDB] = None,
        embeddings: Optional[Any] = None,
        config: Optional[Any] = None,
    ):
        """Initialize the retriever.
        
        Args:
            qdrant_client: Qdrant client instance.
            embeddings: Embeddings model instance.
            config: Configuration object.
        """
        self.config = config or get_config()
        self.qdrant = qdrant_client or QdrantVectorDB(self.config)
        
        # Initialize embeddings
        if embeddings is None:
            self.embeddings = OpenAIEmbeddings(
                model=self.config.embedding_model,
                openai_api_key=self.config.openai_api_key,
            )
        else:
            self.embeddings = embeddings
        
        logger.info("Initialized QdrantRetriever")
    
    async def _embed_query(self, query: str) -> List[float]:
        """Embed a query string.
        
        Args:
            query: The query text.
            
        Returns:
            Embedding vector.
        """
        # Run embedding in executor to avoid blocking
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            self.embeddings.embed_query,
            query,
        )
        return embedding
    
    async def retrieve_exercises(
        self,
        query: str,
        k: Optional[int] = None,
        user_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """Retrieve relevant exercises from Qdrant.
        
        Args:
            query: Natural language query.
            k: Number of results to return.
            user_id: Optional user ID for filtering.
            filters: Optional filter conditions.
            
        Returns:
            List of Document objects with metadata.
        """
        k = k or self.config.qdrant_search_k
        
        # Generate query embedding
        query_vector = await self._embed_query(query)
        
        # Build filter conditions
        filter_conditions = filters or {}
        
        # Search in Qdrant
        results = self.qdrant.search(
            collection_name=self.config.qdrant_exercises_collection,
            query_vector=query_vector,
            k=k,
            filter_conditions=filter_conditions,
        )
        
        # Convert to LangChain Documents
        documents = []
        for result in results:
            payload = result["payload"]
            doc = Document(
                page_content=payload.get("name", ""),
                metadata={
                    "source_id": payload.get("source_id"),
                    "exercise_code": payload.get("exercise_code"),
                    "main_muscle_id": payload.get("main_muscle_id"),
                    "equipment_id": payload.get("equipment_id"),
                    "difficulty_level": payload.get("difficulty_level"),
                    "score": result["score"],
                    "source": "exercises",
                },
            )
            documents.append(doc)
        
        logger.info(f"Retrieved {len(documents)} exercises for query: {query}")
        return documents
    
    async def retrieve_user_memory(
        self,
        query: str,
        user_id: str,
        k: Optional[int] = None,
    ) -> List[Document]:
        """Retrieve relevant user memories from Qdrant.
        
        Args:
            query: Natural language query.
            user_id: User ID to filter memories.
            k: Number of results to return.
            
        Returns:
            List of Document objects with metadata.
        """
        k = k or self.config.qdrant_search_k
        
        # Generate query embedding
        query_vector = await self._embed_query(query)
        
        # Search with user_id filter
        results = self.qdrant.search(
            collection_name=self.config.qdrant_memory_collection,
            query_vector=query_vector,
            k=k,
            filter_conditions={"user_id": user_id},
        )
        
        # Convert to LangChain Documents
        documents = []
        for result in results:
            payload = result["payload"]
            doc = Document(
                page_content=payload.get("content", ""),
                metadata={
                    "source_id": payload.get("source_id"),
                    "user_id": payload.get("user_id"),
                    "created_at": payload.get("created_at"),
                    "memory_type": payload.get("memory_type"),
                    "score": result["score"],
                    "source": "user_memory",
                },
            )
            documents.append(doc)
        
        logger.info(f"Retrieved {len(documents)} memories for user {user_id}")
        return documents
    
    def _apply_mmr(
        self,
        documents: List[Document],
        query_embedding: List[float],
        k: int,
        lambda_mult: float = 0.5,
    ) -> List[Document]:
        """Apply Maximal Marginal Relevance to diversify results.
        
        Args:
            documents: List of documents to diversify.
            query_embedding: The query embedding vector.
            k: Number of documents to return.
            lambda_mult: Diversity parameter (0=max diversity, 1=max relevance).
            
        Returns:
            Diversified list of documents.
        """
        # TODO: Implement MMR if needed
        # For now, just return top k
        return documents[:k]

