"""FastAPI application entrypoint for the Reppy AI service."""

from __future__ import annotations

import json
import logging
import os
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from .common import (
    ChatRequest,
    ExpressAPIClient,
    ensure_required_variables,
    get_openai_client,
    load_prompt_template,
)

LOGGER = logging.getLogger(__name__)

app = FastAPI(title="Reppy AI Service")

_openai_client = get_openai_client()
_express_client = ExpressAPIClient()


@app.on_event("shutdown")
async def _shutdown_event() -> None:
    await _express_client.close()


async def get_express_client() -> ExpressAPIClient:
    return _express_client


@app.post("/chat/stream")
async def stream_chat_response(
    request: ChatRequest,
    express_client: ExpressAPIClient = Depends(get_express_client),
) -> StreamingResponse:
    """Stream responses from OpenAI using the configured prompt template."""

    template = load_prompt_template("chat_response.yaml")
    user_profile = await express_client.get_user_profile(request.user_id)

    conversation = []
    for message in request.messages:
        if hasattr(message, "model_dump"):
            conversation.append(message.model_dump())  # type: ignore[attr-defined]
        else:
            conversation.append(message.dict())

    context = {
        "user_profile": user_profile,
        "conversation": conversation,
        "latest_user_message": request.latest_user_message,
    }
    ensure_required_variables(template, context.keys())

    chat_model = os.getenv("OPENAI_CHAT_MODEL") or os.getenv("OPENAI_COMPLETION_MODEL") or "gpt-4o-mini"
    system_prompt = template.prompt.role.strip()
    response_schema = template.prompt.response_schema or {}
    schema_block = json.dumps(response_schema, indent=2, ensure_ascii=False)

    user_message = (
        f"{template.prompt.instruction.strip()}\n\n"
        f"Conversation:\n{json.dumps(context['conversation'], indent=2, ensure_ascii=False)}\n\n"
        f"User Profile:\n{json.dumps(context['user_profile'], indent=2, ensure_ascii=False)}\n\n"
        f"Respond with valid {template.prompt.response_type} matching this schema:\n{schema_block}"
    )

    try:
        stream = await _openai_client.chat.completions.create(
            model=chat_model,
            stream=True,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
    except Exception as exc:  # pragma: no cover - network failure handling
        LOGGER.exception("Failed to contact OpenAI: %s", exc)
        raise HTTPException(status_code=502, detail="Unable to reach OpenAI") from exc

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield f"data: {delta}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

