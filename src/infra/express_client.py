"""Express server HTTP client with retries and authentication."""

from typing import Any, Dict, List, Optional
from uuid import UUID
import asyncio

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from loguru import logger

from src.config import get_config


class ExpressAPIClient:
    """HTTP client for Express API with retry logic and authentication."""
    
    def __init__(self, config: Optional[Any] = None):
        """Initialize Express API client.
        
        Args:
            config: Configuration object. If None, uses get_config().
        """
        self.config = config or get_config()
        self.base_url = self.config.express_base_url.rstrip("/")
        
        # Setup headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Reppy-FastAPI/1.0",
        }
        if self.config.express_api_key:
            headers["Authorization"] = f"Bearer {self.config.express_api_key}"
        
        # Create async client with timeout and retry settings
        timeout = httpx.Timeout(self.config.express_timeout)
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
        )
        
        logger.info(f"Initialized Express API client: {self.base_url}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    def _should_retry(self, exc: Exception) -> bool:
        """Determine if an exception should trigger a retry.
        
        Args:
            exc: The exception to check.
            
        Returns:
            True if should retry, False otherwise.
        """
        if isinstance(exc, httpx.HTTPStatusError):
            # Retry on 5xx errors, but not 4xx (client errors)
            return 500 <= exc.response.status_code < 600
        if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
            return True
        return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request to Express API.
        
        Args:
            path: API endpoint path (without base URL).
            params: Optional query parameters.
            
        Returns:
            JSON response as dict.
            
        Raises:
            httpx.HTTPStatusError: For 4xx/5xx responses.
        """
        try:
            response = await self.client.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"GET {path} failed with status {e.response.status_code}: {e.response.text}")
            if not self._should_retry(e):
                raise
            raise
        except Exception as e:
            logger.error(f"GET {path} failed: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def post(self, path: str, json: Dict[str, Any]) -> Dict[str, Any]:
        """Make a POST request to Express API.
        
        Args:
            path: API endpoint path (without base URL).
            json: JSON body to send.
            
        Returns:
            JSON response as dict.
            
        Raises:
            httpx.HTTPStatusError: For 4xx/5xx responses.
        """
        try:
            response = await self.client.post(path, json=json)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"POST {path} failed with status {e.response.status_code}: {e.response.text}")
            if not self._should_retry(e):
                raise
            raise
        except Exception as e:
            logger.error(f"POST {path} failed: {e}")
            raise
    
    # Domain-specific methods
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile information.
        
        Args:
            user_id: User UUID.
            
        Returns:
            User profile data.
        """
        return await self.get(f"/api/users/{user_id}/profile")
    
    async def get_active_routines(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's active workout routines.
        
        Args:
            user_id: User UUID.
            
        Returns:
            List of active routines.
        """
        result = await self.get(f"/api/users/{user_id}/routines/active")
        return result.get("routines", [])
    
    async def get_exercise_details(self, exercise_code: str) -> Dict[str, Any]:
        """Get detailed information for an exercise.
        
        Args:
            exercise_code: Exercise code (e.g., 'BARBELL_BENCH_PRESS').
            
        Returns:
            Exercise details including muscles, instructions, etc.
        """
        return await self.get(f"/api/exercises/{exercise_code}")
    
    async def get_exercise_performance_records(
        self,
        user_id: str,
        exercise_code: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get user's performance records for an exercise.
        
        Args:
            user_id: User UUID.
            exercise_code: Exercise code.
            limit: Maximum number of records to return.
            
        Returns:
            List of performance records.
        """
        result = await self.get(
            f"/api/users/{user_id}/exercises/{exercise_code}/records",
            params={"limit": limit},
        )
        return result.get("records", [])
    
    async def calculate_one_rep_max(
        self,
        user_id: str,
        exercise_code: str,
    ) -> Dict[str, Any]:
        """Calculate estimated 1RM for an exercise.
        
        Args:
            user_id: User UUID.
            exercise_code: Exercise code.
            
        Returns:
            Dict with estimated_1rm and calculation details.
        """
        return await self.post(
            f"/api/users/{user_id}/exercises/{exercise_code}/one-rep-max",
            json={},
        )
    
    async def recall_user_memory(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search user's long-term memory.
        
        Args:
            user_id: User UUID.
            query: Natural language query.
            limit: Maximum number of memories to return.
            
        Returns:
            List of relevant memories.
        """
        result = await self.post(
            f"/api/users/{user_id}/memory/search",
            json={"query": query, "limit": limit},
        )
        return result.get("memories", [])
    
    async def find_relevant_exercises(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find exercises matching a semantic query.
        
        Args:
            query: Natural language query about exercises.
            user_id: Optional user ID for personalization.
            limit: Maximum number of exercises to return.
            
        Returns:
            List of relevant exercises.
        """
        payload = {"query": query, "limit": limit}
        if user_id:
            payload["user_id"] = user_id
        
        result = await self.post("/api/exercises/search", json=payload)
        return result.get("exercises", [])
    
    async def save_batch_routines(
        self,
        user_id: str,
        program_id: str,
        routines: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Save a batch of generated routines.
        
        Args:
            user_id: User UUID.
            program_id: Program UUID.
            routines: List of routine objects.
            
        Returns:
            Response with created routine IDs.
        """
        return await self.post(
            "/api/routines/batch",
            json={
                "userId": user_id,
                "programId": program_id,
                "routines": routines,
            },
        )

