"""OCI Functions handler for processing Queue messages."""

import asyncio
import json
from typing import Any, Dict, Iterable, List

from loguru import logger

from .lambda_handler import process_message


def _read_data(data: Any) -> str:
    if data is None:
        return ""
    if isinstance(data, (bytes, bytearray)):
        return data.decode("utf-8")
    if isinstance(data, str):
        return data
    if hasattr(data, "read"):
        return data.read().decode("utf-8")
    return json.dumps(data)


def _parse_json(payload: str) -> Any:
    if not payload:
        return {}
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return payload


def _message_body_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content)


def _normalize_messages(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict) and "messages" in payload:
        messages = payload.get("messages") or []
        normalized: List[Dict[str, Any]] = []
        for message in messages:
            if not isinstance(message, dict):
                normalized.append({"body": _message_body_from_content(message)})
                continue
            body = message.get("body")
            if body is None:
                body = message.get("content")
            if body is None:
                body = message.get("data")
            if body is None:
                body = message.get("payload")
            normalized.append(
                {
                    "messageId": message.get("id")
                    or message.get("messageId")
                    or message.get("message_id"),
                    "body": _message_body_from_content(body),
                }
            )
        return normalized

    if isinstance(payload, dict) and "body" in payload:
        return [payload]

    return [
        {
            "body": _message_body_from_content(payload),
        }
    ]


def _process_messages(messages: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    failed_message_ids: List[str] = []

    for record in messages:
        message_id = record.get("messageId")
        try:
            result = asyncio.run(process_message(record))
            if result.get("success"):
                logger.info(f"Successfully processed message {message_id}")
                results.append({"messageId": message_id, "status": "success"})
            else:
                logger.error(
                    f"Failed to process message {message_id}: {result.get('error')}"
                )
                if message_id:
                    failed_message_ids.append(message_id)
                results.append(
                    {
                        "messageId": message_id,
                        "status": "failed",
                        "error": result.get("error"),
                    }
                )
        except Exception as exc:
            logger.error(f"Exception processing message {message_id}: {exc}")
            if message_id:
                failed_message_ids.append(message_id)
            results.append(
                {
                    "messageId": message_id,
                    "status": "error",
                    "error": str(exc),
                }
            )

    return {
        "results": results,
        "failed_message_ids": failed_message_ids,
    }


def handler(ctx: Any, data: Any) -> Dict[str, Any]:
    """OCI Functions handler.

    Args:
        ctx: OCI Functions context.
        data: Request body stream or payload.

    Returns:
        Processing results.
    """
    payload_raw = _read_data(data)
    payload = _parse_json(payload_raw)
    messages = _normalize_messages(payload)

    logger.info(f"OCI Function invoked with {len(messages)} messages")

    response = _process_messages(messages)

    logger.info(
        "OCI Function processed "
        f"{len(response['results'])} messages, "
        f"{len(response['failed_message_ids'])} failed"
    )
    return response
