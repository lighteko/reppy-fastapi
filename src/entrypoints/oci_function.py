"""OCI Functions entrypoint handler."""

import asyncio
import json
import logging
from typing import Any

from src.config import get_settings
from src.context.adapters.aggregator import DefaultContextAggregator
from src.context.adapters.vm_client import VMApiClient
from src.contracts.messages import RequestPayload, ResultEvent, ResultStatus
from src.emit.oci_streaming import OCITokenStreamer
from src.emit.result_queue import OCIResultPublisher
from src.pipelines.orchestrator import PipelineOrchestrator
from src.utils.logging import configure_logging, set_request_id

logger = logging.getLogger(__name__)


def handler(ctx: Any, data: Any = None) -> str:
    """
    OCI Functions handler.
    
    This is the main entrypoint for OCI Functions.
    Handles both single messages and batch messages from Connector Hub.
    
    Args:
        ctx: OCI Functions context object.
        data: Input data (can be single message or batch).
        
    Returns:
        JSON string with processing results.
    """
    # Initialize settings and logging
    settings = get_settings()
    configure_logging(settings)

    logger.info("OCI Function invoked")

    try:
        # Parse input data
        if data is None:
            return json.dumps({"status": "ok", "processed": 0, "message": "No data provided"})

        # Handle bytes input
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        # Parse JSON if string
        if isinstance(data, str):
            data = json.loads(data)

        # Normalize to list of messages
        messages: list[dict[str, Any]] = []
        if isinstance(data, list):
            # Batch from Connector Hub
            messages = data
        elif isinstance(data, dict):
            # Check if it's a Connector Hub wrapper
            if "data" in data and isinstance(data["data"], list):
                messages = data["data"]
            elif "messages" in data and isinstance(data["messages"], list):
                messages = data["messages"]
            else:
                # Single message
                messages = [data]
        else:
            logger.warning(f"Unexpected data type: {type(data)}")
            return json.dumps({"status": "error", "message": "Invalid input format"})

        # Process messages
        results = asyncio.get_event_loop().run_until_complete(
            process_messages(settings, messages)
        )

        return json.dumps({
            "status": "ok",
            "processed": len(results),
            "results": results,
        })

    except Exception as e:
        logger.error(f"Handler error: {e}", exc_info=True)
        return json.dumps({"status": "error", "message": str(e)})


async def process_messages(
    settings: Any,
    messages: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """
    Process a batch of messages.
    
    Args:
        settings: Application settings.
        messages: List of message dicts.
        
    Returns:
        List of processing results.
    """
    # Initialize components
    vm_client = VMApiClient(settings)
    context_aggregator = DefaultContextAggregator(settings, vm_client)
    token_streamer = OCITokenStreamer(settings)
    result_publisher = OCIResultPublisher(settings)

    orchestrator = PipelineOrchestrator(
        settings=settings,
        vm_client=vm_client,
        context_aggregator=context_aggregator,
        token_streamer=token_streamer,
        result_publisher=result_publisher,
    )

    results: list[dict[str, str]] = []

    try:
        for msg in messages:
            result = await process_single_message(orchestrator, result_publisher, msg)
            results.append(result)
    finally:
        # Cleanup
        await vm_client.close()
        await context_aggregator.close()

    return results


async def process_single_message(
    orchestrator: PipelineOrchestrator,
    result_publisher: Any,
    message: dict[str, Any],
) -> dict[str, str]:
    """
    Process a single message.
    
    Args:
        orchestrator: Pipeline orchestrator.
        result_publisher: Result publisher for errors.
        message: Message dict.
        
    Returns:
        Processing result dict.
    """
    request_id = "unknown"

    try:
        # Extract content from message
        # Connector Hub wraps payload in 'content' field as JSON string
        content = message
        if "content" in message and isinstance(message["content"], str):
            content = json.loads(message["content"])
        elif "data" in message and isinstance(message["data"], str):
            content = json.loads(message["data"])

        # Parse payload
        payload = RequestPayload.model_validate(content)
        request_id = payload.request_id
        set_request_id(request_id)

        logger.info(f"Processing message: {request_id}")

        # Process through pipeline
        await orchestrator.process(payload)

        return {"requestId": request_id, "status": "processed"}

    except Exception as e:
        logger.error(f"Message processing error: {e}", exc_info=True)

        # Try to publish error result
        try:
            if request_id != "unknown":
                await result_publisher.publish(
                    ResultEvent(
                        request_id=request_id,
                        status=ResultStatus.FAILED,
                        error={"code": "PROCESSING_ERROR", "message": str(e)},
                    )
                )
        except Exception as pub_err:
            logger.error(f"Failed to publish error: {pub_err}")

        return {"requestId": request_id, "status": "error", "error": str(e)}

