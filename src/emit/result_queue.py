"""OCI Queue adapter for result publishing."""

import base64
import json
import logging
from typing import Any

import oci
from oci.queue import QueueClient
from oci.queue.models import PutMessagesDetails, PutMessagesDetailsEntry

from src.config import Settings
from src.contracts.messages import ResultEvent
from src.emit.ports import ResultPublisher

logger = logging.getLogger(__name__)


class OCIResultPublisher(ResultPublisher):
    """
    OCI Queue adapter for publishing final results.
    
    Uses OCI SDK to publish messages to a queue.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize OCI Queue client.
        
        Args:
            settings: Application settings.
        """
        self._queue_id = settings.oci_result_queue_id
        self._client: QueueClient | None = None
        self._settings = settings

    def _get_client(self) -> QueueClient:
        """Get or create OCI Queue client."""
        if self._client is None:
            try:
                # Try to use instance principal (for OCI Functions)
                signer = oci.auth.signers.get_resource_principals_signer()
                config: dict[str, Any] = {}
            except Exception:
                # Fall back to config file
                config = oci.config.from_file(profile_name=self._settings.oci_config_profile)
                signer = None

            if signer:
                self._client = QueueClient(config={}, signer=signer)
            else:
                self._client = QueueClient(config)

        return self._client

    async def publish(self, event: ResultEvent) -> None:
        """
        Publish a result event to the result queue.
        
        Args:
            event: Result event with final data.
        """
        try:
            client = self._get_client()

            message_content = json.dumps(event.model_dump_json_compat())

            details = PutMessagesDetails(
                messages=[
                    PutMessagesDetailsEntry(
                        content=base64.b64encode(message_content.encode()).decode()
                    )
                ]
            )

            # Note: This is synchronous in OCI SDK
            # In production, consider using asyncio.to_thread
            response = client.put_messages(self._queue_id, details)

            if response.data.messages:
                logger.info(
                    f"Published result for {event.request_id}: {event.status.value}"
                )
            else:
                logger.warning(f"No confirmation for result publish: {event.request_id}")

        except Exception as e:
            logger.error(f"Failed to publish result for {event.request_id}: {e}")
            raise


class LocalResultPublisher(ResultPublisher):
    """
    Local result publisher for testing/development.
    
    Prints results to console and stores them for inspection.
    """

    def __init__(self) -> None:
        """Initialize local publisher."""
        self._results: list[ResultEvent] = []

    async def publish(self, event: ResultEvent) -> None:
        """Print and store result."""
        self._results.append(event)
        
        print("\n" + "=" * 60)
        print(f"RESULT [{event.status.value}] - {event.request_id}")
        print("=" * 60)
        print(json.dumps(event.model_dump_json_compat(), indent=2, ensure_ascii=False))
        print("=" * 60 + "\n")

    def get_results(self) -> list[ResultEvent]:
        """Get all published results."""
        return self._results.copy()

