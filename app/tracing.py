"""OpenTelemetry export to watsonx Orchestrate trace ingestion."""

from __future__ import annotations

import json
import logging
import os
import ssl
import uuid
from contextlib import contextmanager
from typing import Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import extract
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, Status, StatusCode

from app import config

logger = logging.getLogger(__name__)

_provider: TracerProvider | None = None
_tracer: trace.Tracer | None = None


def tracing_enabled() -> bool:
    return bool(config.OTEL_EXPORT_URL and config.TENANT_ID)


def get_required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _get_mcsp_v2_token() -> str:
    x_api_key = get_required_env("X_API_KEY")
    token_url = get_required_env("MCSP_V2_TOKEN_URL")
    payload = json.dumps({"apikey": x_api_key}).encode("utf-8")
    request = Request(
        token_url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    ssl_context = ssl.create_default_context()
    with urlopen(request, timeout=30, context=ssl_context) as response:
        token_response = json.loads(response.read().decode("utf-8"))
    bearer_token = token_response.get("token") or token_response.get("access_token")
    if not bearer_token:
        raise RuntimeError(f"MCSP v2 token response missing token: {token_response}")
    return str(bearer_token)


def _get_ibmcloud_bearer_token() -> str:
    api_key = get_required_env("API_KEY")
    token_url = get_required_env("TOKEN_URL")
    payload = urlencode(
        {
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": api_key,
        }
    ).encode("utf-8")
    request = Request(
        token_url,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    ssl_context = ssl.create_default_context()
    with urlopen(request, timeout=30, context=ssl_context) as response:
        token_response = json.loads(response.read().decode("utf-8"))
    bearer_token = token_response.get("token") or token_response.get("access_token")
    if not bearer_token:
        raise RuntimeError(f"IAM token response missing access_token: {token_response}")
    return str(bearer_token)


def _build_exporter(otel_export_url: str) -> OTLPSpanExporter:
    auth_type = config.AUTH_TYPE or ""
    if auth_type == "MCSP_v2":
        bearer_token = _get_mcsp_v2_token()
        return OTLPSpanExporter(
            endpoint=otel_export_url,
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
    if (config.TOKEN_URL or "").startswith("https://iam.cloud.ibm.com") and config.API_KEY:
        bearer_token = _get_ibmcloud_bearer_token()
        return OTLPSpanExporter(
            endpoint=otel_export_url,
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
    if config.X_API_KEY:
        return OTLPSpanExporter(
            endpoint=otel_export_url,
            headers={"x-api-key": config.X_API_KEY},
        )
    if config.API_KEY and config.TOKEN_URL:
        bearer_token = _get_ibmcloud_bearer_token()
        return OTLPSpanExporter(
            endpoint=otel_export_url,
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
    raise RuntimeError(
        "Tracing is configured (OTEL_EXPORT_URL/TENANT_ID) but no auth credentials were set"
    )


def setup_tracing() -> None:
    global _provider, _tracer
    if not tracing_enabled():
        logger.info("Tracing disabled: set OTEL_EXPORT_URL and TENANT_ID to enable")
        _tracer = trace.get_tracer(config.SERVICE_NAME)
        return

    os.environ.setdefault(
        "OTEL_RESOURCE_ATTRIBUTES",
        f"tenant.id={config.TENANT_ID},deployment.environment={config.ENVIRONMENT_NAME}",
    )
    resource = Resource.create(
        {
            "service.name": config.SERVICE_NAME,
            "service.version": config.SERVICE_VERSION,
            "application": config.SERVICE_NAME,
        }
    )
    provider = TracerProvider(resource=resource)
    try:
        exporter = _build_exporter(config.OTEL_EXPORT_URL or "")
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info("Tracing enabled -> %s", config.OTEL_EXPORT_URL)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to configure OTLP exporter: %s", exc)
    trace.set_tracer_provider(provider)
    _provider = provider
    _tracer = trace.get_tracer(config.SERVICE_NAME)


def get_tracer() -> trace.Tracer:
    if _tracer is None:
        setup_tracing()
    assert _tracer is not None
    return _tracer


def force_flush() -> None:
    if _provider is not None:
        _provider.force_flush()


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
    """Create a root/child span tagged for watsonx Orchestrate Analytics."""
    if not tracing_enabled() or not agent_id:
        yield None
        return

    tracer = get_tracer()
    parent_ctx = extract(carrier or {})
    token = otel_context.attach(parent_ctx)
    attributes = {
        "agent.id": agent_id,
        "langfuse.session.id": session_id or str(uuid.uuid4()),
        "langfuse.user.id": user_id or f"usr_{uuid.uuid4().hex[:12]}",
        "wxo.protocol": protocol,
    }
    try:
        with tracer.start_as_current_span(name, attributes=attributes) as span:
            try:
                yield span
            except Exception as exc:  # noqa: BLE001
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                raise
    finally:
        otel_context.detach(token)
        force_flush()
