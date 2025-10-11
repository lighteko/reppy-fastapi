"""HTTP client for interacting with the Express.js API service."""

from __future__ import annotations

import os
from typing import Any, Iterable, Optional

import httpx


class ExpressAPIClient:
    """Asynchronous wrapper around the Express API REST endpoints."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        *,
        timeout: float = 30.0,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self._base_url = base_url or os.getenv("EXPRESS_API_URL")
        if not self._base_url:
            raise RuntimeError("EXPRESS_API_URL environment variable must be configured")
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=timeout, transport=transport)

    @property
    def base_url(self) -> str:
        return self._base_url

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "ExpressAPIClient":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close()

    async def get_user_profile(self, user_id: str) -> dict[str, Any]:
        """Fetch a user profile payload from the Express API."""

        response = await self._client.get(f"/users/{user_id}")
        response.raise_for_status()
        return response.json()

    async def get_exercises_by_ids(self, exercise_ids: Iterable[str]) -> list[dict[str, Any]]:
        """Retrieve exercises for the provided list of identifiers."""

        payload = {"exerciseIds": list(exercise_ids)}
        response = await self._client.post("/exercises/bulk", json=payload)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "exercises" in data:
            return list(data["exercises"])
        if isinstance(data, list):
            return list(data)
        raise ValueError("Unexpected response payload when fetching exercises")

    async def save_batch_routines(self, routines_json: dict[str, Any]) -> None:
        """Persist a generated batch of routines via the Express API."""

        response = await self._client.post("/programs/routines/batch", json=routines_json)
        response.raise_for_status()

