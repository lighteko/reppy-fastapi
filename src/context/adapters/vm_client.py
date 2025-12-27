"""VM Internal API client adapter."""

import logging
from typing import Any

import httpx

from src.config import Settings
from src.context.ports.interfaces import VMApiPort

logger = logging.getLogger(__name__)


class VMApiClient(VMApiPort):
    """HTTP client for VM internal API."""

    def __init__(self, settings: Settings) -> None:
        """
        Initialize VM API client.
        
        Args:
            settings: Application settings.
        """
        self._base_url = settings.vm_internal_base_url
        self._token = settings.vm_internal_token
        self._timeout = settings.http_timeout_seconds
        self._client: httpx.AsyncClient | None = None

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=self._get_headers(),
                timeout=httpx.Timeout(self._timeout),
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def claim_idempotency(self, request_id: str) -> bool:
        """
        Claim a request for idempotent processing.
        
        Args:
            request_id: Unique request identifier.
            
        Returns:
            True if claim was successful, False otherwise.
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
            logger.error(f"HTTP error claiming {request_id}: {e.response.status_code}")
            return False
        except httpx.RequestError as e:
            logger.error(f"Request error claiming {request_id}: {e}")
            raise

    async def get_user_profile(self, user_id: str) -> dict[str, Any]:
        """
        Fetch user profile data.
        
        Args:
            user_id: User identifier.
            
        Returns:
            User profile as dictionary.
        """
        client = await self._get_client()
        try:
            response = await client.get(f"/users/{user_id}/profile")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.warning(f"Failed to fetch profile for {user_id}: {e.response.status_code}")
            return {}
        except httpx.RequestError as e:
            logger.error(f"Request error fetching profile for {user_id}: {e}")
            raise

    async def get_active_routines(self, user_id: str) -> dict[str, Any]:
        """
        Fetch user's active routines.
        
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
            logger.warning(f"Failed to fetch routines for {user_id}: {e.response.status_code}")
            return {"routines": []}
        except httpx.RequestError as e:
            logger.error(f"Request error fetching routines for {user_id}: {e}")
            raise

    async def search_exercises(self, query: str) -> dict[str, Any]:
        """
        Search exercise catalog.
        
        Args:
            query: Search query.
            
        Returns:
            Search results with items array.
        """
        client = await self._get_client()
        try:
            response = await client.get(
                "/exercises/search",
                params={"q": query},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.warning(f"Failed to search exercises: {e.response.status_code}")
            return {"items": []}
        except httpx.RequestError as e:
            logger.error(f"Request error searching exercises: {e}")
            raise

