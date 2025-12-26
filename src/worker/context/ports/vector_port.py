"""Port interface for vector search operations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class VectorSearchPort(ABC):
    """Abstract port for vector similarity search."""

    @abstractmethod
    async def search_user_memory(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search user's memory/history using semantic similarity.
        
        Args:
            user_id: The user identifier for filtering.
            query: The search query text.
            limit: Maximum number of results.
            
        Returns:
            List of matching memory items with scores.
        """
        pass

