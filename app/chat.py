"""OpenAI-style chat completions endpoint helpers for watsonx Orchestrate."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, AsyncIterator, Optional

from pydantic import BaseModel, Field

from app import config
from app.graph import SPECIALIST, astream_events, run_sync
from app.telecom import evidence_footer

logger = logging.getLogger(__name__)


class Message(BaseModel):
    role: str
    content: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


class ExtraBody(BaseModel):
    thread_id: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = Field(default=None)
    messages: list[Message]
    stream: Optional[bool] = False
    context: dict[str, Any] = Field(default_factory=dict)
    extra_body: Optional[ExtraBody] = None


class MessageResponse(BaseModel):
    role: str
    content: str


class Choice(BaseModel):
    index: int
    message: MessageResponse
    finish_reason: Optional[str] = "stop"


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[Choice]


def format_sse(payload: dict[str, Any]) -> str:
    return "data: " + json.dumps(payload) + "\n\n"


def _chunk_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text") or "")
            elif isinstance(item, str):
                parts.append(item)
        return "".join(parts)
    return ""


async def stream_chat_completions(
    request: ChatCompletionRequest,
    *,
    thread_id: str,
    protocol: str = "chat_completions",
) -> AsyncIterator[str]:
    model = request.model or config.OPENROUTER_MODEL
    tool_results = []
    try:
        async for event in astream_events(request.messages, protocol=protocol, model=model):
            kind = event.get("event")
            now = int(time.time())
            if kind == "on_chat_model_stream":
                content = _chunk_text(event.get("data", {}).get("chunk", {}).content)
                if not content:
                    continue
                yield format_sse(
                    {
                        "id": str(uuid.uuid4()),
                        "object": "thread.message.delta",
                        "created": now,
                        "thread_id": thread_id,
                        "model": model,
                        "choices": [{"delta": {"role": "assistant", "content": content}}],
                    }
                )
            elif kind == "on_tool_start":
                thinking = {
                    "id": str(uuid.uuid4()),
                    "object": "thread.run.step.delta",
                    "thread_id": thread_id,
                    "model": model,
                    "created": now,
                    "choices": [
                        {
                            "delta": {
                                "role": "assistant",
                                "step_details": {
                                    "type": "thinking",
                                    "content": (
                                        "A tool call is required to answer this trial question."
                                    ),
                                },
                            }
                        }
                    ],
                }
                yield format_sse(thinking)
                tool_struct = {
                    "id": str(uuid.uuid4()),
                    "object": "thread.run.step.delta",
                    "thread_id": thread_id,
                    "model": model,
                    "created": now,
                    "choices": [
                        {
                            "delta": {
                                "role": "assistant",
                                "step_details": {
                                    "type": "tool_calls",
                                    "tool_calls": [
                                        {
                                            "id": event.get("run_id"),
                                            "name": event.get("name"),
                                            "args": event.get("data", {}).get("input"),
                                        }
                                    ],
                                },
                            }
                        }
                    ],
                }
                yield format_sse(tool_struct)
            elif kind == "on_tool_end":
                output = event.get("data", {}).get("output")
                if SPECIALIST:
                    tool_results.append(output)
                content = getattr(output, "content", "") if output is not None else ""
                tool_call_id = event.get("run_id")
                yield format_sse(
                    {
                        "id": str(uuid.uuid4()),
                        "object": "thread.run.step.delta",
                        "thread_id": thread_id,
                        "model": model,
                        "created": now,
                        "choices": [
                            {
                                "delta": {
                                    "role": "assistant",
                                    "step_details": {
                                        "type": "tool_response",
                                        "name": event.get("name"),
                                        "tool_call_id": tool_call_id,
                                        "content": content,
                                    },
                                }
                            }
                        ],
                    }
                )
        if SPECIALIST:
            yield format_sse(
                {
                    "id": str(uuid.uuid4()),
                    "object": "thread.message.delta",
                    "created": int(time.time()),
                    "thread_id": thread_id,
                    "model": model,
                    "choices": [{"delta": {
                        "role": "assistant",
                        "content": evidence_footer(tool_results, SPECIALIST, protocol),
                    }}],
                }
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("chat stream failed")
        yield format_sse(
            {
                "id": str(uuid.uuid4()),
                "object": "thread.message.delta",
                "created": int(time.time()),
                "thread_id": thread_id,
                "model": model,
                "choices": [
                    {
                        "delta": {
                            "role": "assistant",
                            "content": f"Error: {exc}",
                        }
                    }
                ],
            }
        )


def sync_chat_completion(
    request: ChatCompletionRequest,
    *,
    protocol: str = "chat_completions",
) -> ChatCompletionResponse:
    model = request.model or config.OPENROUTER_MODEL
    content = run_sync(request.messages, protocol=protocol, model=model)
    return ChatCompletionResponse(
        id=str(uuid.uuid4()),
        created=int(time.time()),
        model=model,
        choices=[
            Choice(
                index=0,
                message=MessageResponse(role="assistant", content=content),
                finish_reason="stop",
            )
        ],
    )
