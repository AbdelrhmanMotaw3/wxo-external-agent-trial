"""FastAPI entrypoint: chat completions + A2A + observability demo routes."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app import config
from app.auth import require_agent_auth
from app.a2a_server import mount_a2a_routes
from app.chat import ChatCompletionRequest, stream_chat_completions, sync_chat_completion
from app.graph import run_sync
from app.tracing import agent_span, setup_tracing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="watsonx Orchestrate External Agent Trial",
    version=config.SERVICE_VERSION,
    description=(
        "LangGraph + FastAPI external agent for chat completions and A2A 0.3.0 trials, "
        "with OpenRouter LLM and OTLP traces to watsonx Orchestrate."
    ),
)


@app.on_event("startup")
async def on_startup() -> None:
    setup_tracing()
    logger.info("Public URL: %s", config.PUBLIC_URL)
    logger.info("Default model: %s", config.OPENROUTER_MODEL)


# A2A routes are mounted at process import time so OpenAPI/discovery stay stable.
try:
    mount_a2a_routes(app, protocol_label="a2a")
except Exception as exc:  # noqa: BLE001
    logger.exception("Failed to mount A2A routes at import time: %s", exc)


class DemoRequest(BaseModel):
    message: str = Field(..., description="User message for an observability-only demo call")
    session_id: Optional[str] = None


def _carrier_from_request(request: Request) -> dict[str, str]:
    carrier: dict[str, str] = {}
    for key in ("traceparent", "tracestate"):
        value = request.headers.get(key)
        if value:
            carrier[key] = value
    return carrier


def _resolve_thread_id(
    header_value: Optional[str],
    request: ChatCompletionRequest,
) -> str:
    if header_value:
        return header_value
    if request.extra_body and request.extra_body.thread_id:
        return request.extra_body.thread_id
    return str(uuid.uuid4())


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Protect Orchestrate-facing and demo endpoints with the shared trial token."""
    path = request.url.path
    protected_prefixes = ("/chat/completions", "/demo/")
    # Root POST is A2A JSON-RPC; agent card stays public for discovery.
    needs_auth = path.startswith(protected_prefixes) or (
        path == "/" and request.method.upper() == "POST"
    )
    if needs_auth:
        expected = config.AGENT_AUTH_TOKEN
        authorization = request.headers.get("authorization")
        x_api_key = request.headers.get("x-api-key")
        bearer_ok = False
        if authorization and authorization.lower().startswith("bearer "):
            bearer_ok = authorization.split(" ", 1)[1].strip() == expected
        api_key_ok = bool(x_api_key and x_api_key == expected)
        if not (bearer_ok or api_key_ok):
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing credentials"})
    return await call_next(request)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": config.SERVICE_NAME,
        "model": config.OPENROUTER_MODEL,
        "public_url": config.PUBLIC_URL,
    }


@app.post("/chat/completions")
async def chat_completions(
    request_body: ChatCompletionRequest,
    request: Request,
    x_ibm_thread_id: Optional[str] = Header(None, alias="X-IBM-THREAD-ID"),
    _: None = Depends(require_agent_auth),
):
    thread_id = _resolve_thread_id(x_ibm_thread_id, request_body)
    carrier = _carrier_from_request(request)
    agent_id = config.CHAT_AGENT_ID

    if request_body.stream:
        async def event_generator():
            with agent_span(
                name="chat_completions",
                agent_id=agent_id,
                protocol="chat_completions",
                session_id=thread_id,
                carrier=carrier,
            ):
                async for chunk in stream_chat_completions(
                    request_body,
                    thread_id=thread_id,
                    protocol="chat_completions",
                ):
                    yield chunk

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    with agent_span(
        name="chat_completions",
        agent_id=agent_id,
        protocol="chat_completions",
        session_id=thread_id,
        carrier=carrier,
    ):
        response = sync_chat_completion(request_body, protocol="chat_completions")
    return JSONResponse(content=response.model_dump())


@app.post("/demo/chat")
async def demo_chat(body: DemoRequest, request: Request):
    """Observability-only path: same graph, tagged with CHAT_OBS_AGENT_ID."""
    agent_id = config.CHAT_OBS_AGENT_ID
    if not agent_id:
        raise HTTPException(
            status_code=400,
            detail="Set CHAT_OBS_AGENT_ID after registering the observability-only chat agent",
        )
    session_id = body.session_id or str(uuid.uuid4())
    with agent_span(
        name="demo_chat",
        agent_id=agent_id,
        protocol="chat_completions_obs_only",
        session_id=session_id,
        carrier=_carrier_from_request(request),
    ):
        answer = run_sync(
            [{"role": "user", "content": body.message}],
            protocol="chat_completions_obs_only",
        )
    return {
        "agent_id": agent_id,
        "session_id": session_id,
        "protocol": "chat_completions_obs_only",
        "answer": answer,
    }


@app.post("/demo/a2a")
async def demo_a2a(body: DemoRequest, request: Request):
    """Observability-only path: same graph, tagged with A2A_OBS_AGENT_ID."""
    agent_id = config.A2A_OBS_AGENT_ID
    if not agent_id:
        raise HTTPException(
            status_code=400,
            detail="Set A2A_OBS_AGENT_ID after registering the observability-only A2A agent",
        )
    session_id = body.session_id or str(uuid.uuid4())
    with agent_span(
        name="demo_a2a",
        agent_id=agent_id,
        protocol="a2a_obs_only",
        session_id=session_id,
        carrier=_carrier_from_request(request),
    ):
        answer = run_sync(
            [{"role": "user", "content": body.message}],
            protocol="a2a_obs_only",
        )
    return {
        "agent_id": agent_id,
        "session_id": session_id,
        "protocol": "a2a_obs_only",
        "answer": answer,
    }


# Wrap A2A JSON-RPC handling with use-and-observability tracing when possible.
@app.middleware("http")
async def a2a_trace_middleware(request: Request, call_next):
    if request.url.path == "/" and request.method.upper() == "POST" and config.A2A_AGENT_ID:
        with agent_span(
            name="a2a_jsonrpc",
            agent_id=config.A2A_AGENT_ID,
            protocol="a2a",
            carrier=_carrier_from_request(request),
        ):
            return await call_next(request)
    return await call_next(request)
