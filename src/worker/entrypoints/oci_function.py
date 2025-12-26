"""
OCI Functions entrypoint.

Handles batch messages from OCI Queue via Connector Hub.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Union

from ..contracts import WorkerRequest, ResultEvent, ResultStatus
from ..pipelines import PipelineOrchestrator
from ..utils import setup_logging

logger = logging.getLogger(__name__)


def handler(event: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    OCI Functions handler.
    
    Handles both single and batch events from Connector Hub.
    
    Args:
        event: Single event dict or list of events (batch).
        
    Returns:
        Response dict with processing results.
    """
    # Setup logging
    setup_logging()
    
    # Normalize to list
    if isinstance(event, dict):
        messages = [event]
    elif isinstance(event, list):
        messages = event
    else:
        logger.error(f"Invalid event type: {type(event)}")
        return {"error": "Invalid event format", "processed": 0}
    
    logger.info(f"Received {len(messages)} message(s) to process")
    
    # Process all messages
    results = asyncio.get_event_loop().run_until_complete(
        process_messages(messages)
    )
    
    # Summarize results
    succeeded = sum(1 for r in results if r.get("status") == "SUCCEEDED")
    failed = sum(1 for r in results if r.get("status") == "FAILED")
    clarify = sum(1 for r in results if r.get("status") == "CLARIFY")
    skipped = sum(1 for r in results if r.get("skipped", False))
    
    logger.info(
        f"Processing complete: succeeded={succeeded}, failed={failed}, "
        f"clarify={clarify}, skipped={skipped}"
    )
    
    return {
        "processed": len(results),
        "succeeded": succeeded,
        "failed": failed,
        "clarify": clarify,
        "skipped": skipped,
        "results": results,
    }


async def process_messages(
    messages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Process a batch of messages asynchronously.
    
    Each message is processed independently with its own error handling.
    
    Args:
        messages: List of message dicts.
        
    Returns:
        List of result dicts.
    """
    async with PipelineOrchestrator() as orchestrator:
        results = []
        
        for msg in messages:
            result = await process_single_message(orchestrator, msg)
            results.append(result)
        
        return results


async def process_single_message(
    orchestrator: PipelineOrchestrator,
    message: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Process a single message with error handling.
    
    Args:
        orchestrator: Pipeline orchestrator instance.
        message: Single message dict from queue.
        
    Returns:
        Result dict.
    """
    request_id = "unknown"
    
    try:
        # Extract content from message
        # Connector Hub wraps the original message
        content = message.get("content")
        
        if content is None:
            # Maybe it's already the payload
            payload = message
        elif isinstance(content, str):
            # Parse JSON content
            payload = json.loads(content)
        elif isinstance(content, dict):
            payload = content
        else:
            raise ValueError(f"Invalid content type: {type(content)}")
        
        # Parse into WorkerRequest
        request = WorkerRequest.model_validate(payload)
        request_id = request.requestId
        
        logger.info(f"[{request_id}] Processing message")
        
        # Process through orchestrator
        result = await orchestrator.process(request)
        
        return {
            "requestId": request_id,
            "status": result.status.value,
            "skipped": result.final.get("skipped", False) if result.final else False,
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse message content: {e}")
        return {
            "requestId": request_id,
            "status": "FAILED",
            "error": f"JSON parse error: {e}",
        }
    except Exception as e:
        logger.error(f"[{request_id}] Message processing failed: {e}", exc_info=True)
        return {
            "requestId": request_id,
            "status": "FAILED",
            "error": str(e),
        }


# Alternative handler for direct invocation
def handle_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Direct request handler for testing or alternative invocation.
    
    Args:
        payload: Request payload dict.
        
    Returns:
        Result dict.
    """
    setup_logging()
    
    async def _process():
        async with PipelineOrchestrator() as orchestrator:
            request = WorkerRequest.model_validate(payload)
            result = await orchestrator.process(request)
            return result.model_dump(mode="json")
    
    return asyncio.get_event_loop().run_until_complete(_process())

