"""OTLP export with expiring-token refresh and per-request trace identity.

IBM Cloud IAM is the verified target. Existing MCSP/header authentication paths
are retained, but are not an assertion of AWS or on-premises compatibility.
"""

from __future__ import annotations

import json
import logging
import re
import ssl
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Lock
from typing import Callable, Iterator
from urllib.error import URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

import requests
from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import extract
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, SpanKind, Status, StatusCode

from app import config

logger = logging.getLogger(__name__)
_provider: TracerProvider | None = None
_tracer: trace.Tracer | None = None
_identity: ContextVar[dict[str, str] | None] = ContextVar(
    "external_agent_identity", default=None
)
_request_context: ContextVar[dict | None] = ContextVar(
    "external_request_context", default=None
)


class TraceContextMiddleware:
    """Carry incoming trace headers through the full ASGI request/task lifecycle."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1")
            for k, v in scope.get("headers", [])
        }
        carrier = {k: headers[k] for k in ("traceparent", "tracestate") if k in headers}
        token = _request_context.set(
            {"carrier": carrier, "session_id": headers.get("x-ibm-thread-id")}
        )
        try:
            await self.app(scope, receive, send)
        finally:
            _request_context.reset(token)


def incoming_request_context() -> dict:
    return _request_context.get() or {}


def tracing_enabled() -> bool:
    return bool(config.OTEL_EXPORT_URL and config.TENANT_ID)


def safe_content(value) -> str:
    """Bound recorded content and redact common credential fields."""

    def redact(obj):
        if isinstance(obj, dict):
            return {
                str(k): "[REDACTED]"
                if any(
                    s in str(k).lower()
                    for s in (
                        "authorization",
                        "api_key",
                        "apikey",
                        "access_token",
                        "refresh_token",
                        "password",
                        "secret",
                    )
                )
                else redact(v)
                for k, v in obj.items()
            }
        if isinstance(obj, (list, tuple)):
            return [redact(v) for v in obj]
        if hasattr(obj, "model_dump"):
            return redact(obj.model_dump())
        return obj

    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            pass
    value = redact(value)
    text = (
        value
        if isinstance(value, str)
        else json.dumps(value, ensure_ascii=False, default=str)
    )
    text = re.sub(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", text)
    text = re.sub(r"sk-or-v1-[A-Za-z0-9]+", "[REDACTED]", text)
    for secret in (
        config.API_KEY,
        config.X_API_KEY,
        config.AGENT_AUTH_TOKEN,
        config.OPENROUTER_API_KEY,
    ):
        if secret and len(secret) >= 8:
            text = text.replace(secret, "[REDACTED]")
    return text[: config.TRACE_MAX_CONTENT_CHARS]


def record_content(span: Span | None, key: str, value) -> None:
    if span is not None and span.is_recording() and config.TRACE_CAPTURE_CONTENT:
        span.set_attribute(key, safe_content(value))


def mark_error(span: Span | None, error: BaseException) -> None:
    if span is not None and span.is_recording():
        span.set_attribute("error.type", type(error).__name__)
        span.set_status(Status(StatusCode.ERROR, type(error).__name__))
        span.add_event(
            "exception",
            {
                "exception.type": type(error).__name__,
                "exception.message": safe_content(str(error))
                if config.TRACE_CAPTURE_CONTENT
                else type(error).__name__,
            },
        )


class RefreshingBearerToken:
    """Cache by monotonic TTL and serialize refreshes across export threads."""

    def __init__(self, fetch: Callable[[], tuple[str, float]], *, clock=time.monotonic):
        self._fetch = fetch
        self._clock = clock
        self._token = None
        self._refresh_at = 0.0
        self._lock = Lock()

    def get(self) -> str:
        with self._lock:
            if self._token is None or self._clock() >= self._refresh_at:
                token, ttl = self._fetch()
                if not token or ttl <= 0:
                    raise RuntimeError(
                        "Token endpoint returned an invalid token or lifetime"
                    )
                self._token = token
                self._refresh_at = self._clock() + ttl - min(30.0, ttl * 0.1)
            return self._token

    def invalidate(self, rejected_token: str) -> None:
        with self._lock:
            if self._token == rejected_token:
                self._refresh_at = 0.0


def _token_response(request: Request) -> tuple[str, float]:
    try:
        with urlopen(
            request, timeout=10, context=ssl.create_default_context()
        ) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (URLError, OSError, ValueError):
        raise requests.RequestException(
            "Trace token request failed; check IAM credentials, access and connectivity"
        ) from None
    token = data.get("access_token") or data.get("token")
    ttl = data.get("expires_in")
    if ttl is None and data.get("expiration"):
        ttl = float(data["expiration"]) - time.time()
    if not token or ttl is None or float(ttl) <= 0:
        raise requests.RequestException(
            "Trace token response is missing a token or a valid expiry"
        )
    return str(token), float(ttl)


def _fetch_ibmcloud_token() -> tuple[str, float]:
    if not config.API_KEY:
        raise requests.RequestException("Missing API_KEY for trace export")
    if config.TOKEN_URL != "https://iam.cloud.ibm.com/identity/token":
        raise requests.RequestException(
            "IBM Cloud tracing requires the IBM Cloud IAM token endpoint"
        )
    request = Request(
        config.TOKEN_URL,
        data=urlencode(
            {
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": config.API_KEY,
            }
        ).encode(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    return _token_response(request)


def _fetch_mcsp_token() -> tuple[str, float]:
    if not config.X_API_KEY or not config.MCSP_V2_TOKEN_URL:
        raise requests.RequestException(
            "Missing existing MCSP trace authentication configuration"
        )
    request = Request(
        config.MCSP_V2_TOKEN_URL,
        data=json.dumps({"apikey": config.X_API_KEY}).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    return _token_response(request)


class RefreshingOTLPSession(requests.Session):
    """Authenticate each batch; refresh and retry exactly once after a 401."""

    def __init__(self, tokens: RefreshingBearerToken, endpoint: str):
        super().__init__()
        self._tokens = tokens
        self._endpoint = endpoint

    def send(self, request, **kwargs):
        if request.url != self._endpoint:
            raise requests.RequestException(
                "Refusing to send trace credentials to an unexpected URL"
            )
        token = self._tokens.get()
        request.headers["Authorization"] = "Bearer " + token
        kwargs["allow_redirects"] = False
        response = super().send(request, **kwargs)
        if response.status_code == 401:
            response.close()
            self._tokens.invalidate(token)
            request.headers["Authorization"] = "Bearer " + self._tokens.get()
            response = super().send(request, **kwargs)
        return response


def _build_exporter(endpoint: str) -> OTLPSpanExporter:
    parsed = urlsplit(endpoint)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("OTEL_EXPORT_URL must be an HTTPS ingestion endpoint")
    if config.AUTH_TYPE == "MCSP_v2":
        session = RefreshingOTLPSession(
            RefreshingBearerToken(_fetch_mcsp_token), endpoint
        )
        return OTLPSpanExporter(
            endpoint=endpoint,
            session=session,
            timeout=config.OTEL_EXPORT_TIMEOUT_SECONDS,
        )
    if config.API_KEY:
        if config.TOKEN_URL != "https://iam.cloud.ibm.com/identity/token":
            raise ValueError(
                "This trace implementation targets IBM Cloud IAM; AWS is not configured"
            )
        session = RefreshingOTLPSession(
            RefreshingBearerToken(_fetch_ibmcloud_token), endpoint
        )
        return OTLPSpanExporter(
            endpoint=endpoint,
            session=session,
            timeout=config.OTEL_EXPORT_TIMEOUT_SECONDS,
        )
    if config.X_API_KEY:
        return OTLPSpanExporter(
            endpoint=endpoint,
            headers={"x-api-key": config.X_API_KEY},
            timeout=config.OTEL_EXPORT_TIMEOUT_SECONDS,
        )
    raise ValueError(
        "Tracing requires IBM Cloud API_KEY (or existing explicitly configured legacy auth)"
    )


def setup_tracing() -> None:
    global _provider, _tracer
    if _provider is not None:
        return
    if not tracing_enabled():
        logger.info("Tracing disabled: set OTEL_EXPORT_URL and TENANT_ID to enable")
        _tracer = trace.get_tracer(config.SERVICE_NAME)
        return
    if config.ENVIRONMENT_NAME not in ("draft", "live"):
        raise ValueError("ENVIRONMENT_NAME must be draft or live")
    resource = Resource.create(
        {
            "service.name": config.SERVICE_NAME,
            "service.version": config.SERVICE_VERSION,
            "application": config.SERVICE_NAME,
            "tenant.id": config.TENANT_ID,
            "deployment.environment": config.ENVIRONMENT_NAME,
            "environment.name": config.ENVIRONMENT_NAME,
        }
    )
    exporter = _build_exporter(config.OTEL_EXPORT_URL or "")
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    _provider = provider
    _tracer = provider.get_tracer("telecom-external-agent", config.SERVICE_VERSION)
    logger.info(
        "OTLP export configured for service %s; IAM is authenticated on export",
        config.SERVICE_NAME,
    )


def get_tracer() -> trace.Tracer:
    if _tracer is None:
        setup_tracing()
    assert _tracer is not None
    return _tracer


def force_flush() -> None:
    if _provider is not None and not _provider.force_flush(
        timeout_millis=config.OTEL_FLUSH_TIMEOUT_MS
    ):
        logger.warning("Trace flush timed out; export may complete asynchronously")


def shutdown_tracing() -> None:
    global _provider, _tracer
    if _provider is not None:
        _provider.shutdown()
    _provider = None
    _tracer = None


@contextmanager
def agent_span(
    *,
    name: str,
    agent_id: str | None,
    protocol: str,
    session_id: str | None = None,
    user_id: str | None = None,
    carrier: dict[str, str] | None = None,
) -> Iterator[Span | None]:
    if not tracing_enabled() or not agent_id:
        yield None
        return
    parent = extract(carrier) if carrier else otel_context.get_current()
    attributes = {
        "agent.id": agent_id,
        "environment.name": config.ENVIRONMENT_NAME,
        "langfuse.session.id": session_id or str(uuid.uuid4()),
        "langfuse.user.id": user_id or "external-client",
        "wxo.protocol": protocol,
        "gen_ai.operation.name": "invoke_agent",
        "gen_ai.agent.name": config.SERVICE_NAME,
    }
    attributes["agent.name"] = config.SERVICE_NAME
    if config.WORKSPACE_ID:
        attributes["workspace.id"] = config.WORKSPACE_ID
    identity_token = _identity.set(attributes)
    try:
        with get_tracer().start_as_current_span(
            name,
            context=parent,
            kind=SpanKind.SERVER,
            attributes=attributes,
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            try:
                yield span
            except BaseException as exc:
                mark_error(span, exc)
                raise
    finally:
        _identity.reset(identity_token)
        force_flush()


@contextmanager
def graph_execution(model: str):
    """Create actual-timed child spans with explicit cross-thread parent context."""
    identity = _identity.get()
    if not tracing_enabled() or not identity:
        yield []
        return
    from app.trace_callbacks import AgentTraceCallback

    with get_tracer().start_as_current_span(
        "agent.graph",
        attributes=identity,
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        callback = AgentTraceCallback(
            get_tracer(), otel_context.get_current(), identity, model
        )
        error = None
        try:
            yield [callback]
        except BaseException as exc:
            error = exc
            mark_error(span, exc)
            raise
        finally:
            callback.close(error)
