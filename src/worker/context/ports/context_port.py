"""Port interface for context data fetching from VM internal API."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ContextPort(ABC):
    """Abstract port for fetching context data from VM internal API."""

    @abstractmethod
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch user profile data.
        
        Args:
            user_id: The user identifier.
            
        Returns:
            User profile as a dictionary.
        """
        pass

    @abstractmethod
    async def get_active_routines(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch user's active routines/programs.
        
        Args:
            user_id: The user identifier.
            
        Returns:
            Active routines data.
        """
        pass

    @abstractmethod
    async def search_exercises(
        self, query: str, limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search for exercises by query.
        
        Args:
            query: Search query string.
            limit: Maximum number of results.
            
        Returns:
            Exercise search results.
        """
        pass

