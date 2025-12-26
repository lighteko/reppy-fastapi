"""Port interface for result queue publishing."""

from abc import ABC, abstractmethod

from ...contracts import ResultEvent


class ResultQueuePort(ABC):
    """Abstract port for publishing result events."""

    @abstractmethod
    async def publish(self, event: ResultEvent) -> None:
        """
        Publish a result event to the result queue.
        
        Args:
            event: Result event to publish.
        """
        pass

