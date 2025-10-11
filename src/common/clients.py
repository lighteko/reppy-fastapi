"""Client factory helpers for shared integrations."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from openai import AsyncOpenAI
from qdrant_client import QdrantClient


class MissingEnvironmentVariable(RuntimeError):
    """Raised when a required environment variable is not defined."""

    def __init__(self, variable: str) -> None:
        super().__init__(f"Environment variable '{variable}' must be defined")
        self.variable = variable


def _get_env(name: str, *, required: bool = True, default: Optional[str] = None) -> Optional[str]:
    """Fetch an environment variable and optionally enforce its presence."""

    value = os.getenv(name, default)
    if required and not value:
        raise MissingEnvironmentVariable(name)
    return value


@lru_cache(maxsize=1)
def get_openai_client() -> AsyncOpenAI:
    """Return a singleton AsyncOpenAI client configured from the environment."""

    api_key = _get_env("OPENAI_API_KEY")
    base_url = _get_env("OPENAI_BASE_URL", required=False)
    organization = _get_env("OPENAI_ORGANIZATION", required=False)
    project = _get_env("OPENAI_PROJECT", required=False)

    return AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        organization=organization,
        project=project,
    )


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """Return a singleton Qdrant client configured from the environment."""

    api_key = _get_env("QDRANT_API_KEY", required=False)
    prefer_grpc = _get_env("QDRANT_PREFER_GRPC", required=False, default="false")
    prefer_grpc_bool = str(prefer_grpc).lower() in {"1", "true", "yes"}

    url = _get_env("QDRANT_URL", required=False)
    if url:
        return QdrantClient(url=url, api_key=api_key, prefer_grpc=prefer_grpc_bool)

    host = _get_env("QDRANT_HOST", required=False)
    if not host:
        raise MissingEnvironmentVariable("QDRANT_URL or QDRANT_HOST")

    port_str = _get_env("QDRANT_PORT", required=False, default="6333")
    port = int(port_str)
    return QdrantClient(host=host, port=port, api_key=api_key, prefer_grpc=prefer_grpc_bool)

