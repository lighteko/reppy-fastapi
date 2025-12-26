"""
Context aggregator - fetches context based on required_context from planner.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List

from .ports import ContextPort, VectorSearchPort

logger = logging.getLogger(__name__)


class ContextAggregator:
    """
    Aggregates context from multiple sources based on required_context keys.
    
    Supported keys:
    - active_routines: User's current routines from VM API
    - user_memory: Semantic search in Qdrant
    - exercise_catalog: Exercise search from VM API
    """

    def __init__(
        self,
        context_port: ContextPort,
        vector_port: VectorSearchPort,
    ):
        """
        Initialize aggregator with ports.
        
        Args:
            context_port: Port for VM internal API.
            vector_port: Port for vector search (Qdrant).
        """
        self._context_port = context_port
        self._vector_port = vector_port

    async def aggregate(
        self,
        user_id: str,
        required_context: List[str],
        args: Dict[str, Any],
        fallback_query: str,
        request_id: str,
    ) -> Dict[str, Any]:
        """
        Aggregate context based on required keys.
        
        Args:
            user_id: User identifier.
            required_context: List of context keys to fetch.
            args: Arguments from planner (may contain 'query').
            fallback_query: Fallback query if args.query is missing.
            request_id: Request ID for logging.
            
        Returns:
            Dict with fetched context for each required key.
        """
        context: Dict[str, Any] = {}
        tasks = []
        keys = []
        
        start_time = time.perf_counter()
        
        # Build tasks for each required context
        for key in required_context:
            if key == "active_routines":
                tasks.append(self._fetch_active_routines(user_id))
                keys.append(key)
            elif key == "user_memory":
                query = args.get("query") or fallback_query
                tasks.append(self._fetch_user_memory(user_id, query))
                keys.append(key)
            elif key == "exercise_catalog":
                query = args.get("query") or fallback_query
                tasks.append(self._fetch_exercise_catalog(query))
                keys.append(key)
            else:
                logger.warning(f"[{request_id}] Unknown context key: {key}")
        
        if tasks:
            # Fetch all contexts in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for key, result in zip(keys, results):
                if isinstance(result, Exception):
                    logger.error(f"[{request_id}] Error fetching {key}: {result}")
                    context[key] = {}
                else:
                    context[key] = result
        
        elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"[{request_id}] Context aggregation completed in {elapsed:.2f}ms "
            f"(keys: {keys})"
        )
        
        return context

    async def _fetch_active_routines(self, user_id: str) -> Dict[str, Any]:
        """Fetch active routines from VM API."""
        return await self._context_port.get_active_routines(user_id)

    async def _fetch_user_memory(
        self, user_id: str, query: str
    ) -> Dict[str, Any]:
        """Fetch user memory from Qdrant."""
        memories = await self._vector_port.search_user_memory(
            user_id=user_id,
            query=query,
            limit=5,
        )
        return {"items": memories, "query": query}

    async def _fetch_exercise_catalog(self, query: str) -> Dict[str, Any]:
        """Search exercise catalog from VM API."""
        return await self._context_port.search_exercises(query=query, limit=10)

