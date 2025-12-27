"""Interface definitions for context fetching."""

from abc import ABC, abstractmethod
from typing import Any


class IdempotencyPort(ABC):
    """Port for idempotency claim operations."""

    @abstractmethod
    async def claim(self, request_id: str) -> bool:
        """
        Attempt to claim a request for processing.
        
        Args:
            request_id: Unique request identifier.
            
        Returns:
            True if claim was successful, False if already claimed.
        """
        ...


class VMApiPort(ABC):
    """Port for VM internal API operations."""

    @abstractmethod
    async def claim_idempotency(self, request_id: str) -> bool:
        """Claim a request for idempotent processing."""
        ...

    @abstractmethod
    async def get_user_profile(self, user_id: str) -> dict[str, Any]:
        """Fetch user profile data."""
        ...

    @abstractmethod
    async def get_active_routines(self, user_id: str) -> dict[str, Any]:
        """Fetch user's active routines."""
        ...

    @abstractmethod
    async def search_exercises(self, query: str) -> dict[str, Any]:
        """Search exercise catalog."""
        ...


class QdrantPort(ABC):
    """Port for Qdrant vector search operations."""

    @abstractmethod
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
        ...


class ContextAggregator(ABC):
    """Port for aggregating context from multiple sources."""

    @abstractmethod
    async def aggregate(
        self,
        user_id: str,
        required_context: list[str],
        query: str | None = None,
    ) -> dict[str, Any]:
        """
        Aggregate context from multiple sources based on required keys.
        
        Args:
            user_id: User identifier.
            required_context: List of context keys to fetch.
            query: Optional query for search operations.
            
        Returns:
            Dictionary with fetched context data.
        """
        ...

