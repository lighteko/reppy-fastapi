"""Port definitions for emit operations."""

from abc import ABC, abstractmethod

from src.contracts.messages import ResultEvent, TokenStreamEvent


class TokenStreamer(ABC):
    """Port for streaming tokens to clients."""

    @abstractmethod
    async def publish(self, event: TokenStreamEvent) -> None:
        """
        Publish a token streaming event.
        
        Args:
            event: Token stream event with delta text.
        """
        ...

    @abstractmethod
    async def flush(self, request_id: str) -> None:
        """
        Flush any buffered tokens for a request.
        
        Args:
            request_id: Request identifier.
        """
        ...


class ResultPublisher(ABC):
    """Port for publishing final results."""

    @abstractmethod
    async def publish(self, event: ResultEvent) -> None:
        """
        Publish a result event to the result queue.
        
        Args:
            event: Result event with final data.
        """
        ...

