"""
OCI Streaming adapter for token streaming.

Note: This is a simplified implementation. In production, you would use
the OCI SDK (oci.streaming.StreamClient) with proper authentication.
"""

import base64
import json
import logging
from typing import List, Optional

import httpx

from ..ports import TokenStreamPort
from ...contracts import TokenStreamEvent
from ...config import settings

logger = logging.getLogger(__name__)


class OCIStreamingAdapter(TokenStreamPort):
    """
    OCI Streaming adapter for publishing token stream events.
    
    Uses HTTP API to publish messages to OCI Streaming.
    In production, use the OCI Python SDK for proper authentication.
    """

    def __init__(
        self,
        stream_id: str | None = None,
        batch_size: int = 10,
    ):
        """
        Initialize OCI Streaming adapter.
        
        Args:
            stream_id: OCI Stream OCID. Defaults to settings.
            batch_size: Number of events to batch before sending.
        """
        self._stream_id = stream_id or settings.OCI_STREAM_ID
        self._batch_size = batch_size
        self._buffer: List[TokenStreamEvent] = []
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def publish(self, event: TokenStreamEvent) -> None:
        """
        Publish a token stream event.
        
        Events are buffered and sent in batches for efficiency.
        
        Args:
            event: Token stream event to publish.
        """
        self._buffer.append(event)
        
        if len(self._buffer) >= self._batch_size:
            await self.flush()

    async def flush(self) -> None:
        """Flush buffered events to OCI Streaming."""
        if not self._buffer:
            return
        
        events_to_send = self._buffer[:]
        self._buffer.clear()
        
        try:
            await self._send_messages(events_to_send)
            logger.debug(f"Flushed {len(events_to_send)} token events to stream")
        except Exception as e:
            logger.error(f"Failed to flush token events: {e}")
            # Re-add to buffer for retry on next flush
            self._buffer = events_to_send + self._buffer

    async def _send_messages(self, events: List[TokenStreamEvent]) -> None:
        """
        Send messages to OCI Streaming.
        
        TODO: Replace with actual OCI SDK implementation.
        This is a stub that shows the expected interface.
        """
        # In production, use oci.streaming.StreamClient:
        #
        # from oci.streaming import StreamClient
        # from oci.streaming.models import PutMessagesDetails, PutMessagesDetailsEntry
        # 
        # client = StreamClient(config, service_endpoint=stream_endpoint)
        # messages = [
        #     PutMessagesDetailsEntry(
        #         key=event.requestId.encode(),
        #         value=event.model_dump_json().encode(),
        #     )
        #     for event in events
        # ]
        # client.put_messages(
        #     stream_id=self._stream_id,
        #     put_messages_details=PutMessagesDetails(messages=messages),
        # )
        
        # Stub implementation - log the events
        for event in events:
            logger.info(
                f"[STREAM] requestId={event.requestId} seq={event.seq} "
                f"delta_len={len(event.delta)}"
            )

    async def close(self) -> None:
        """Close the adapter and flush remaining events."""
        await self.flush()
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "OCIStreamingAdapter":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()

