"""SQS worker entrypoint for asynchronous program generation jobs."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import ValidationError

from .common import ExpressAPIClient, GenerateProgramJob, RAGOrchestrator

LOGGER = logging.getLogger(__name__)


class SQSWorker:
    """Polls an SQS queue for program generation jobs."""

    def __init__(
        self,
        *,
        queue_url: str,
        sqs_client: Optional[Any] = None,
        express_client: Optional[ExpressAPIClient] = None,
        orchestrator: Optional[RAGOrchestrator] = None,
        wait_time_seconds: int = 10,
        visibility_timeout: int = 60,
        max_messages: int = 1,
    ) -> None:
        self.queue_url = queue_url
        self.wait_time_seconds = wait_time_seconds
        self.visibility_timeout = visibility_timeout
        self.max_messages = max_messages
        self.sqs_client = sqs_client or boto3.client(
            "sqs", region_name=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
        )
        self.express_client = express_client or ExpressAPIClient()
        self.orchestrator = orchestrator or RAGOrchestrator(express_client=self.express_client)
        self._stopped = asyncio.Event()

    @classmethod
    def from_environment(cls) -> "SQSWorker":
        queue_url = os.getenv("SQS_QUEUE_URL")
        if not queue_url:
            raise RuntimeError("SQS_QUEUE_URL environment variable must be defined")
        wait_time = int(os.getenv("SQS_WAIT_TIME", "10"))
        visibility_timeout = int(os.getenv("SQS_VISIBILITY_TIMEOUT", "60"))
        max_messages = int(os.getenv("SQS_MAX_MESSAGES", "1"))
        return cls(
            queue_url=queue_url,
            wait_time_seconds=wait_time,
            visibility_timeout=visibility_timeout,
            max_messages=max_messages,
        )

    async def run(self) -> None:
        LOGGER.info("Starting SQS worker polling loop")
        while not self._stopped.is_set():
            messages = await self._receive_messages()
            if not messages:
                await asyncio.sleep(1)
                continue
            for message in messages:
                await self._process_message(message)

    async def stop(self) -> None:
        LOGGER.info("Stopping SQS worker")
        self._stopped.set()
        await self.express_client.close()

    async def _receive_messages(self) -> list[dict[str, Any]]:
        try:
            response = await asyncio.to_thread(
                self.sqs_client.receive_message,
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=self.max_messages,
                WaitTimeSeconds=self.wait_time_seconds,
                VisibilityTimeout=self.visibility_timeout,
            )
        except (BotoCoreError, ClientError) as exc:
            LOGGER.exception("Error receiving SQS messages: %s", exc)
            await asyncio.sleep(5)
            return []
        return response.get("Messages", [])

    async def _process_message(self, message: dict[str, Any]) -> None:
        receipt_handle = message.get("ReceiptHandle")
        if not receipt_handle:
            LOGGER.warning("Received message without receipt handle; discarding")
            return

        try:
            body = json.loads(message.get("Body", "{}"))
            if hasattr(GenerateProgramJob, "model_validate"):
                job = GenerateProgramJob.model_validate(body)  # type: ignore[attr-defined]
            else:
                job = GenerateProgramJob.parse_obj(body)
        except (json.JSONDecodeError, ValidationError) as exc:
            LOGGER.exception("Invalid message payload: %s", exc)
            await self._delete_message(receipt_handle)
            return

        try:
            routines = await self.orchestrator.generate_routine_from_rag(job)
            try:
                payload = routines.dict()
            except AttributeError:  # pydantic v2 compatibility
                payload = routines.model_dump()  # type: ignore[attr-defined]
            await self.express_client.save_batch_routines(payload)
        except Exception as exc:  # pragma: no cover - network and LLM failures
            LOGGER.exception("Error processing job for user %s: %s", job.user_id, exc)
            await self._handle_processing_failure(receipt_handle)
            return

        await self._delete_message(receipt_handle)

    async def _delete_message(self, receipt_handle: str) -> None:
        try:
            await asyncio.to_thread(
                self.sqs_client.delete_message, QueueUrl=self.queue_url, ReceiptHandle=receipt_handle
            )
        except (BotoCoreError, ClientError) as exc:
            LOGGER.exception("Failed to delete SQS message: %s", exc)

    async def _handle_processing_failure(self, receipt_handle: str) -> None:
        try:
            await asyncio.to_thread(
                self.sqs_client.change_message_visibility,
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=0,
            )
        except (BotoCoreError, ClientError) as exc:
            LOGGER.exception("Failed to reset message visibility: %s", exc)


async def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    worker = SQSWorker.from_environment()
    try:
        await worker.run()
    finally:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())

