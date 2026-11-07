"""Opt-in live ingestion probe. Uses synthetic model responses, not OpenRouter."""

import json
from unittest.mock import patch

from langchain_core.messages import AIMessage

from app import config, graph, tracing
from tests.test_trace_integration import ScriptedModel

profile = config.AGENT_PROFILE
tool, args = (
    ("get_customer_account", {"customer_id": "CUST-1007"})
    if profile == "customer_account"
    else ("get_active_incidents", {"area_id": "AREA-003", "service": "home_internet"})
)
fake = ScriptedModel(
    responses=[
        AIMessage(
            content="", tool_calls=[{"name": tool, "args": args, "id": "probe-lookup"}]
        ),
        AIMessage(content="Synthetic telemetry probe; no paid model call."),
    ]
)
tracing.setup_tracing()
try:
    with tracing.agent_span(
        name="telecom_ibmcloud_trace_verification",
        agent_id=config.CHAT_AGENT_ID
        if profile == "customer_account"
        else config.A2A_AGENT_ID,
        protocol="offline_verification",
        session_id="telecom-otel-verification-2026-11-07",
    ) as span:
        if span is None:
            raise RuntimeError("Trace probe requires export configuration and Agent ID")
        span.set_attribute("test.synthetic_model", True)
        trace_id = format(span.get_span_context().trace_id, "032x")
        with patch.object(graph, "build_llm", return_value=fake):
            answer = graph.run_sync(
                [{"role": "user", "content": "Run the synthetic telecom lookup."}],
                protocol="offline_verification",
                model="offline-scripted-model",
            )
        tracing.record_content(span, "output", answer)
    print(
        json.dumps(
            {
                "profile": profile,
                "trace_id": trace_id,
                "agent_id": config.CHAT_AGENT_ID
                if profile == "customer_account"
                else config.A2A_AGENT_ID,
                "paid_model_calls": 0,
            }
        ),
        flush=True,
    )
finally:
    tracing.shutdown_tracing()
