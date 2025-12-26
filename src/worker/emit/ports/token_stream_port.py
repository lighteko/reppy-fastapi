"""Port interface for token streaming."""

from abc import ABC, abstractmethod

from ...contracts import TokenStreamEvent


class TokenStreamPort(ABC):
    """Abstract port for publishing token stream events."""

    @abstractmethod
    async def publish(self, event: TokenStreamEvent) -> None:
        """
        Publish a token stream event.
        
        Args:
            event: Token stream event to publish.
        """
        pass

    @abstractmethod
    async def flush(self) -> None:
        """Flush any buffered events."""
        pass

