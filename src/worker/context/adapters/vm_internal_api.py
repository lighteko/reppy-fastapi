"""
VM Internal API adapter - implements ContextPort and IdempotencyPort.

All database operations go through the VM's internal HTTP API.
"""

import logging
from typing import Any, Dict

import httpx

from ..ports import ContextPort, IdempotencyPort
from ...config import settings

logger = logging.getLogger(__name__)


class VMInternalAPIAdapter(ContextPort, IdempotencyPort):
    """
    Adapter for VM internal API.
    
    Handles:
    - Idempotency claims
    - User profile fetching
    - Active routines fetching
    - Exercise search
    """

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = 30.0,
    ):
        """
        Initialize the adapter.
        
        Args:
            base_url: VM internal API base URL. Defaults to settings.
            token: Bearer token for auth. Defaults to settings.
            timeout: Request timeout in seconds.
        """
        self._base_url = (base_url or settings.VM_INTERNAL_BASE_URL).rstrip("/")
        self._token = token or settings.VM_INTERNAL_TOKEN
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def claim(self, request_id: str) -> bool:
        """
        Attempt to claim a request for idempotent processing.
        
        Args:
            request_id: Unique request identifier.
            
        Returns:
            True if claimed successfully, False if already processed.
        """
        client = await self._get_client()
        try:
            response = await client.post(
                "/idempotency/claim",
                json={"requestId": request_id},
            )
            response.raise_for_status()
            data = response.json()
            claimed = data.get("claimed", False)
            logger.debug(f"Idempotency claim for {request_id}: {claimed}")
            return claimed
        except httpx.HTTPStatusError as e:
            logger.error(f"Idempotency claim failed for {request_id}: {e}")
            # If claim endpoint fails, assume we should NOT process
            # to avoid duplicate processing
            return False
        except Exception as e:
            logger.error(f"Idempotency claim error for {request_id}: {e}")
            return False

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch user profile from VM internal API.
        
        Args:
            user_id: User identifier.
            
        Returns:
            User profile data.
        """
        client = await self._get_client()
        try:
            response = await client.get(f"/users/{user_id}/profile")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.warning(f"Failed to fetch user profile for {user_id}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error fetching user profile for {user_id}: {e}")
            return {}

    async def get_active_routines(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch user's active routines from VM internal API.
        
        Args:
            user_id: User identifier.
            
        Returns:
            Active routines data.
        """
        client = await self._get_client()
        try:
            response = await client.get(f"/users/{user_id}/active-routines")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.warning(f"Failed to fetch active routines for {user_id}: {e}")
            return {"routines": []}
        except Exception as e:
            logger.error(f"Error fetching active routines for {user_id}: {e}")
            return {"routines": []}

    async def search_exercises(
        self, query: str, limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search exercises via VM internal API.
        
        Args:
            query: Search query.
            limit: Max results.
            
        Returns:
            Exercise search results.
        """
        client = await self._get_client()
        try:
            response = await client.get(
                "/exercises/search",
                params={"q": query, "limit": limit},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.warning(f"Failed to search exercises for '{query}': {e}")
            return {"items": []}
        except Exception as e:
            logger.error(f"Error searching exercises for '{query}': {e}")
            return {"items": []}

    async def __aenter__(self) -> "VMInternalAPIAdapter":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()

