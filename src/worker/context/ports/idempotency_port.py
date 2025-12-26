"""Port interface for idempotency checking."""

from abc import ABC, abstractmethod


class IdempotencyPort(ABC):
    """Abstract port for idempotency claim operations."""

    @abstractmethod
    async def claim(self, request_id: str) -> bool:
        """
        Attempt to claim a request for processing.
        
        Args:
            request_id: The unique request identifier.
            
        Returns:
            True if claim was successful (this worker should process),
            False if already claimed/processed by another worker.
        """
        pass

