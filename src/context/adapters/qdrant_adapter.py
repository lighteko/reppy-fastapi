"""Qdrant vector search adapter."""

import logging
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from src.config import Settings

logger = logging.getLogger(__name__)


class QdrantAdapter:
    """Qdrant client adapter for user memory search."""

    def __init__(self, settings: Settings) -> None:
        """
        Initialize Qdrant adapter.
        
        Args:
            settings: Application settings.
        """
        self._url = settings.qdrant_url
        self._api_key = settings.qdrant_api_key
        self._collection = settings.qdrant_collection_memory
        self._client: AsyncQdrantClient | None = None

    async def _get_client(self) -> AsyncQdrantClient:
        """Get or create async Qdrant client."""
        if self._client is None:
            self._client = AsyncQdrantClient(
                url=self._url,
                api_key=self._api_key,
            )
        return self._client

    async def close(self) -> None:
        """Close the Qdrant client."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def search_user_memory(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Search user memory using semantic search.
        
        Args:
            user_id: User identifier for filtering.
            query: Search query text.
            limit: Maximum results to return.
            
        Returns:
            List of memory entries with scores.
        """
        client = await self._get_client()
        
        try:
            # Search with user_id filter
            results = await client.query(
                collection_name=self._collection,
                query_text=query,
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

            # Convert to list of dicts
            memories: list[dict[str, Any]] = []
            for point in results:
                entry: dict[str, Any] = {
                    "id": str(point.id),
                    "score": point.score,
                    "content": point.payload.get("content", "") if point.payload else "",
                    "metadata": point.metadata if hasattr(point, "metadata") else {},
                }
                if point.payload:
                    entry["payload"] = point.payload
                memories.append(entry)

            logger.debug(f"Found {len(memories)} memories for user {user_id}")
            return memories

        except Exception as e:
            logger.error(f"Qdrant search error for user {user_id}: {e}")
            return []

