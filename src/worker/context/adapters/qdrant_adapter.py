"""
Qdrant adapter for vector similarity search.

Used for user memory retrieval based on semantic similarity.
"""

import logging
from typing import Any, Dict, List, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from ..ports import VectorSearchPort
from ...config import settings

logger = logging.getLogger(__name__)


class QdrantAdapter(VectorSearchPort):
    """
    Qdrant vector database adapter.
    
    Handles semantic search for user memory/history.
    """

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        collection_name: str | None = None,
    ):
        """
        Initialize Qdrant adapter.
        
        Args:
            url: Qdrant server URL. Defaults to settings.
            api_key: Qdrant API key. Defaults to settings.
            collection_name: Collection name. Defaults to settings.
        """
        self._url = url or settings.QDRANT_URL
        self._api_key = api_key or settings.QDRANT_API_KEY
        self._collection = collection_name or settings.QDRANT_COLLECTION_MEMORY
        self._client: Optional[AsyncQdrantClient] = None
        self._embedding_model = None

    async def _get_client(self) -> AsyncQdrantClient:
        """Get or create Qdrant client."""
        if self._client is None:
            self._client = AsyncQdrantClient(
                url=self._url,
                api_key=self._api_key,
            )
        return self._client

    async def _get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using Gemini.
        
        Args:
            text: Text to embed.
            
        Returns:
            Embedding vector.
        """
        # Use Google's embedding model
        import google.generativeai as genai
        
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        
        result = await genai.embed_content_async(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_query",
        )
        return result["embedding"]

    async def search_user_memory(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search user's memory using semantic similarity.
        
        Args:
            user_id: User identifier for filtering.
            query: Search query text.
            limit: Maximum results.
            
        Returns:
            List of matching memory items.
        """
        try:
            client = await self._get_client()
            
            # Generate query embedding
            query_vector = await self._get_embedding(query)
            
            # Search with user filter
            results = await client.search(
                collection_name=self._collection,
                query_vector=query_vector,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_id),
                        )
                    ]
                ),
                limit=limit,
            )
            
            # Format results
            memories = []
            for result in results:
                memories.append({
                    "id": str(result.id),
                    "score": result.score,
                    "content": result.payload.get("content", ""),
                    "metadata": result.payload.get("metadata", {}),
                    "timestamp": result.payload.get("timestamp"),
                })
            
            logger.debug(f"Found {len(memories)} memories for user {user_id}")
            return memories
            
        except Exception as e:
            logger.error(f"Error searching user memory: {e}")
            return []

    async def close(self) -> None:
        """Close the Qdrant client."""
        if self._client:
            await self._client.close()
            self._client = None

    async def __aenter__(self) -> "QdrantAdapter":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()

