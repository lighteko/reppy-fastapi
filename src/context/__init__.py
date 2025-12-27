"""Context module - data fetching ports and adapters."""

from src.context.ports.interfaces import (
    ContextAggregator,
    IdempotencyPort,
    QdrantPort,
    VMApiPort,
)
from src.context.adapters.vm_client import VMApiClient
from src.context.adapters.qdrant_adapter import QdrantAdapter
from src.context.adapters.aggregator import DefaultContextAggregator

__all__ = [
    # Ports
    "ContextAggregator",
    "IdempotencyPort",
    "QdrantPort",
    "VMApiPort",
    # Adapters
    "DefaultContextAggregator",
    "QdrantAdapter",
    "VMApiClient",
]

