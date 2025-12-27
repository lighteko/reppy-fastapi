"""Context aggregator implementation."""

import asyncio
import logging
from typing import Any

from src.config import Settings
from src.context.ports.interfaces import ContextAggregator
from src.context.adapters.vm_client import VMApiClient
from src.context.adapters.qdrant_adapter import QdrantAdapter

logger = logging.getLogger(__name__)


class DefaultContextAggregator(ContextAggregator):
    """
    Aggregates context from multiple sources based on required keys.
    
    Supports parallel fetching for better latency.
    """

    def __init__(
        self,
        settings: Settings,
        vm_client: VMApiClient | None = None,
        qdrant_adapter: QdrantAdapter | None = None,
    ) -> None:
        """
        Initialize context aggregator.
        
        Args:
            settings: Application settings.
            vm_client: Optional pre-configured VM client.
            qdrant_adapter: Optional pre-configured Qdrant adapter.
        """
        self._settings = settings
        self._vm_client = vm_client or VMApiClient(settings)
        self._qdrant = qdrant_adapter or QdrantAdapter(settings)
        self._owns_clients = vm_client is None or qdrant_adapter is None

    async def close(self) -> None:
        """Close owned clients."""
        if self._owns_clients:
            await self._vm_client.close()
            await self._qdrant.close()

    async def aggregate(
        self,
        user_id: str,
        required_context: list[str],
        query: str | None = None,
    ) -> dict[str, Any]:
        """
        Aggregate context from multiple sources.
        
        Args:
            user_id: User identifier.
            required_context: List of context keys to fetch.
            query: Optional query for search operations.
            
        Returns:
            Dictionary with fetched context data.
        """
        if not required_context:
            return {}

        context: dict[str, Any] = {}
        tasks: dict[str, asyncio.Task[Any]] = {}

        # Create tasks for each required context
        for key in required_context:
            if key == "active_routines":
                tasks[key] = asyncio.create_task(
                    self._fetch_active_routines(user_id)
                )
            elif key == "user_memory":
                search_query = query or ""
                tasks[key] = asyncio.create_task(
                    self._fetch_user_memory(user_id, search_query)
                )
            elif key == "exercise_catalog":
                search_query = query or ""
                tasks[key] = asyncio.create_task(
                    self._fetch_exercise_catalog(search_query)
                )
            else:
                logger.warning(f"Unknown context key: {key}")

        # Wait for all tasks
        if tasks:
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for key, result in zip(tasks.keys(), results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching {key}: {result}")
                    context[key] = {}
                else:
                    context[key] = result

        logger.debug(f"Aggregated context keys: {list(context.keys())}")
        return context

    async def _fetch_active_routines(self, user_id: str) -> dict[str, Any]:
        """Fetch active routines from VM API."""
        return await self._vm_client.get_active_routines(user_id)

    async def _fetch_user_memory(
        self,
        user_id: str,
        query: str,
    ) -> dict[str, Any]:
        """Fetch user memory from Qdrant."""
        if not query:
            return {"memories": []}
        
        memories = await self._qdrant.search_user_memory(user_id, query)
        return {"memories": memories}

    async def _fetch_exercise_catalog(self, query: str) -> dict[str, Any]:
        """Fetch exercise catalog from VM API."""
        if not query:
            return {"items": []}
        
        return await self._vm_client.search_exercises(query)

