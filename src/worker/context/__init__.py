"""Context fetching module - ports and adapters for external data sources."""

from .ports import (
    ContextPort,
    IdempotencyPort,
    VectorSearchPort,
)
from .adapters import (
    VMInternalAPIAdapter,
    QdrantAdapter,
)
from .aggregator import ContextAggregator

__all__ = [
    "ContextPort",
    "IdempotencyPort",
    "VectorSearchPort",
    "VMInternalAPIAdapter",
    "QdrantAdapter",
    "ContextAggregator",
]

