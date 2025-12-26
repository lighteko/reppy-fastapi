"""
OCI Queue adapter for result publishing.

Note: This is a simplified implementation. In production, you would use
the OCI SDK (oci.queue.QueueClient) with proper authentication.
"""

import json
import logging
from typing import Optional

import httpx

from ..ports import ResultQueuePort
from ...contracts import ResultEvent
from ...config import settings

logger = logging.getLogger(__name__)


class OCIQueueAdapter(ResultQueuePort):
    """
    OCI Queue adapter for publishing result events.
    
    Uses HTTP API to publish messages to OCI Queue.
    In production, use the OCI Python SDK for proper authentication.
    """

    def __init__(
        self,
        queue_id: str | None = None,
    ):
        """
        Initialize OCI Queue adapter.
        
        Args:
            queue_id: OCI Queue OCID. Defaults to settings.
        """
        self._queue_id = queue_id or settings.OCI_RESULT_QUEUE_ID
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def publish(self, event: ResultEvent) -> None:
        """
        Publish a result event to the result queue.
        
        Args:
            event: Result event to publish.
        """
        try:
            await self._send_message(event)
            logger.info(
                f"[RESULT] requestId={event.requestId} status={event.status.value}"
            )
        except Exception as e:
            logger.error(f"Failed to publish result event: {e}")
            raise

    async def _send_message(self, event: ResultEvent) -> None:
        """
        Send message to OCI Queue.
        
        TODO: Replace with actual OCI SDK implementation.
        This is a stub that shows the expected interface.
        """
        # In production, use oci.queue.QueueClient:
        #
        # from oci.queue import QueueClient
        # from oci.queue.models import PutMessagesDetails, PutMessagesDetailsEntry
        # 
        # client = QueueClient(config, service_endpoint=queue_endpoint)
        # client.put_messages(
        #     queue_id=self._queue_id,
        #     put_messages_details=PutMessagesDetails(
        #         messages=[
        #             PutMessagesDetailsEntry(content=event.model_dump_json())
        #         ]
        #     ),
        # )
        
        # Stub implementation - log the event
        event_data = event.model_dump(mode="json")
        logger.debug(f"[QUEUE] Publishing: {json.dumps(event_data, ensure_ascii=False)}")

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "OCIQueueAdapter":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()

