"""OCI Streaming adapter for token streaming."""

import base64
import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import oci  # noqa: F401
    from oci.streaming import StreamClient  # noqa: F401
    from oci.streaming.models import PutMessagesDetails, PutMessagesDetailsEntry  # noqa: F401
else:
    StreamClient = Any  # type: ignore[assignment]
    PutMessagesDetails = Any  # type: ignore[assignment]
    PutMessagesDetailsEntry = Any  # type: ignore[assignment]

from src.config import Settings
from src.contracts.messages import TokenStreamEvent
from src.emit.ports import TokenStreamer

logger = logging.getLogger(__name__)


class OCITokenStreamer(TokenStreamer):
    """
    OCI Streaming adapter for publishing token deltas.
    
    Uses OCI SDK to publish messages to a stream.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize OCI Streaming client.
        
        Args:
            settings: Application settings.
        """
        self._stream_id = settings.oci_stream_id
        self._client: StreamClient | None = None
        self._settings = settings
        self._buffer: dict[str, list[TokenStreamEvent]] = {}
        self._buffer_size = 10  # Batch size for publishing

    def _get_client(self) -> StreamClient:
        """Get or create OCI Streaming client."""
        if self._client is None:
            # Import OCI SDK lazily so local_runner can run without it installed.
            import oci  # type: ignore
            from oci.streaming import StreamClient  # type: ignore

            try:
                # Try to use instance principal (for OCI Functions)
                signer = oci.auth.signers.get_resource_principals_signer()
                config: dict[str, Any] = {}
            except Exception:
                # Fall back to config file
                config = oci.config.from_file(profile_name=self._settings.oci_config_profile)
                signer = None
            
            # Get stream endpoint from stream ID
            # In production, you'd get this from the Stream's messages_endpoint
            # For now, we construct a placeholder
            if signer:
                self._client = StreamClient(config={}, signer=signer)
            else:
                self._client = StreamClient(config)
        
        return self._client

    async def publish(self, event: TokenStreamEvent) -> None:
        """
        Publish a token streaming event.
        
        Buffers events and publishes in batches for efficiency.
        
        Args:
            event: Token stream event.
        """
        request_id = event.request_id
        
        if request_id not in self._buffer:
            self._buffer[request_id] = []
        
        self._buffer[request_id].append(event)
        
        # Publish when buffer reaches threshold
        if len(self._buffer[request_id]) >= self._buffer_size:
            await self._publish_batch(request_id)

    async def _publish_batch(self, request_id: str) -> None:
        """Publish buffered events as a batch."""
        if request_id not in self._buffer or not self._buffer[request_id]:
            return

        events = self._buffer[request_id]
        self._buffer[request_id] = []

        try:
            # Lazy import for optional OCI dependency.
            from oci.streaming.models import PutMessagesDetails, PutMessagesDetailsEntry  # type: ignore

            client = self._get_client()
            
            messages = [
                PutMessagesDetailsEntry(
                    key=base64.b64encode(request_id.encode()).decode(),
                    value=base64.b64encode(
                        json.dumps(e.model_dump_json_compat()).encode()
                    ).decode(),
                )
                for e in events
            ]

            details = PutMessagesDetails(messages=messages)
            
            # Note: This is synchronous in OCI SDK
            # In production, consider using asyncio.to_thread
            response = client.put_messages(self._stream_id, details)
            
            if response.data.failures and response.data.failures > 0:
                logger.warning(
                    f"Some messages failed to publish: {response.data.failures} failures"
                )
            else:
                logger.debug(f"Published {len(messages)} tokens for {request_id}")

        except Exception as e:
            logger.error(f"Failed to publish tokens for {request_id}: {e}")
            # Re-add events to buffer for retry
            self._buffer[request_id] = events + self._buffer.get(request_id, [])

    async def flush(self, request_id: str) -> None:
        """
        Flush any buffered tokens for a request.
        
        Args:
            request_id: Request identifier.
        """
        await self._publish_batch(request_id)


class LocalTokenStreamer(TokenStreamer):
    """
    Local token streamer for testing/development.
    
    Prints tokens to console instead of OCI Streaming.
    """

    def __init__(self) -> None:
        """Initialize local streamer."""
        self._tokens: dict[str, list[str]] = {}

    async def publish(self, event: TokenStreamEvent) -> None:
        """Print token to console."""
        if event.request_id not in self._tokens:
            self._tokens[event.request_id] = []
        
        self._tokens[event.request_id].append(event.delta)
        print(event.delta, end="", flush=True)

    async def flush(self, request_id: str) -> None:
        """Print newline to console."""
        if request_id in self._tokens:
            print()  # Newline
            logger.debug(
                f"Flushed {len(self._tokens[request_id])} tokens for {request_id}"
            )

