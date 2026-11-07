"""Offline trace contract tests; no tenant, secrets, or paid LLM are used."""

import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch
from uuid import uuid4

os.environ.setdefault("OTEL_EXPORT_URL", "")
os.environ.setdefault("TENANT_ID", "")

import requests
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, LLMResult
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from app import tracing


class TokenRefreshTests(unittest.TestCase):
    def test_real_otlp_exporter_uses_refreshing_transport_and_protobuf(self):
        from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
            ExportTraceServiceRequest,
        )

        calls = []

        def send(_session, prepared, **kwargs):
            calls.append((prepared.headers["Authorization"], prepared.body))
            response = requests.Response()
            response.status_code = 401 if len(calls) == 1 else 200
            response._content = b""
            response._content_consumed = True
            return response

        with (
            patch.object(tracing.config, "API_KEY", "dummy-iam-key"),
            patch.object(
                tracing.config, "TOKEN_URL", "https://iam.cloud.ibm.com/identity/token"
            ),
            patch.object(tracing.config, "AUTH_TYPE", ""),
            patch.object(
                tracing,
                "_fetch_ibmcloud_token",
                side_effect=[("expired", 3600), ("fresh", 3600)],
            ),
            patch.object(requests.Session, "send", send),
        ):
            exporter = tracing._build_exporter("https://collector.example/traces")
            provider = TracerProvider()
            provider.add_span_processor(SimpleSpanProcessor(exporter))
            with provider.get_tracer("transport-test").start_as_current_span(
                "transport-proof", attributes={"agent.id": "test-agent"}
            ):
                pass
            provider.shutdown()
        self.assertEqual([x[0] for x in calls], ["Bearer expired", "Bearer fresh"])
        self.assertEqual(calls[0][1], calls[1][1])
        payload = ExportTraceServiceRequest.FromString(calls[1][1])
        self.assertEqual(
            payload.resource_spans[0].scope_spans[0].spans[0].name, "transport-proof"
        )

    def test_reuses_token_then_refreshes_before_expiry(self):
        clock = Mock(return_value=100.0)
        fetch = Mock(side_effect=[("first", 120), ("second", 120)])
        cache = tracing.RefreshingBearerToken(fetch, clock=clock)
        self.assertEqual(cache.get(), "first")
        clock.return_value = 150.0
        self.assertEqual(cache.get(), "first")
        clock.return_value = 211.0
        self.assertEqual(cache.get(), "second")
        self.assertEqual(fetch.call_count, 2)

    def test_concurrent_exports_share_one_refresh(self):
        fetch = Mock(return_value=("shared", 3600))
        cache = tracing.RefreshingBearerToken(fetch)
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(
                list(pool.map(lambda _: cache.get(), range(24))), ["shared"] * 24
            )
        self.assertEqual(fetch.call_count, 1)

    def test_iam_request_is_form_encoded_and_response_expiry_is_used(self):
        reply = Mock()
        reply.__enter__ = Mock(return_value=reply)
        reply.__exit__ = Mock(return_value=False)
        reply.read.return_value = b'{"access_token":"example-token","expires_in":3600}'
        with (
            patch.object(tracing.config, "API_KEY", "example-key"),
            patch.object(
                tracing.config, "TOKEN_URL", "https://iam.cloud.ibm.com/identity/token"
            ),
            patch.object(tracing, "urlopen", return_value=reply) as send,
        ):
            token, ttl = tracing._fetch_ibmcloud_token()
        self.assertEqual((token, ttl), ("example-token", 3600.0))
        body = send.call_args.args[0].data.decode()
        self.assertIn(
            "grant_type=urn%3Aibm%3Aparams%3Aoauth%3Agrant-type%3Aapikey", body
        )
        self.assertIn("apikey=example-key", body)

    def test_401_refreshes_once_and_resends_exact_batch(self):
        fetch = Mock(side_effect=[("old", 3600), ("new", 3600)])
        session = tracing.RefreshingOTLPSession(
            tracing.RefreshingBearerToken(fetch),
            "https://collector.example/inject/traces",
        )
        request = requests.Request(
            "POST", "https://collector.example/inject/traces", data=b"otlp-batch"
        ).prepare()
        seen = []

        def send(_session, prepared, **kwargs):
            seen.append(
                (
                    prepared.headers["Authorization"],
                    prepared.body,
                    kwargs.get("allow_redirects"),
                )
            )
            response = requests.Response()
            response.status_code = 401 if len(seen) == 1 else 200
            response._content = b""
            response._content_consumed = True
            return response

        with patch.object(requests.Session, "send", send):
            self.assertEqual(session.send(request).status_code, 200)
        self.assertEqual(
            seen,
            [
                ("Bearer old", b"otlp-batch", False),
                ("Bearer new", b"otlp-batch", False),
            ],
        )

    def test_unauthorized_retry_is_bounded(self):
        cache = tracing.RefreshingBearerToken(Mock(return_value=("bad", 3600)))
        session = tracing.RefreshingOTLPSession(
            cache, "https://collector.example/traces"
        )
        request = requests.Request(
            "POST", "https://collector.example/traces", data=b"batch"
        ).prepare()
        response = requests.Response()
        response.status_code = 401
        response._content = b""
        response._content_consumed = True
        with patch.object(requests.Session, "send", return_value=response) as send:
            self.assertEqual(session.send(request).status_code, 401)
        self.assertEqual(send.call_count, 2)


class SpanTests(unittest.TestCase):
    def setUp(self):
        self.exporter = InMemorySpanExporter()
        self.provider = TracerProvider()
        self.provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        self.tracer = self.provider.get_tracer("offline-test")
        self.patchers = [
            patch.object(tracing, "get_tracer", return_value=self.tracer),
            patch.object(tracing, "tracing_enabled", return_value=True),
            patch.object(tracing.config, "TRACE_CAPTURE_CONTENT", True),
        ]
        for p in self.patchers:
            p.start()

    def tearDown(self):
        for p in reversed(self.patchers):
            p.stop()
        self.provider.shutdown()

    def test_incoming_trace_context_and_child_identity(self):
        carrier = {
            "traceparent": "00-11111111111111111111111111111111-2222222222222222-01"
        }
        with tracing.agent_span(
            name="invoke_agent Account",
            agent_id="account-id",
            protocol="chat_completions",
            session_id="session-1",
            carrier=carrier,
        ) as root:
            with tracing.graph_execution("fake-model") as callbacks:
                run = uuid4()
                callbacks[0].on_chat_model_start(
                    {"name": "model"}, [[AIMessage(content="hello")]], run_id=run
                )
                callbacks[0].on_llm_end(
                    LLMResult(
                        generations=[
                            [
                                ChatGeneration(
                                    message=AIMessage(
                                        content="answer",
                                        usage_metadata={
                                            "input_tokens": 12,
                                            "output_tokens": 3,
                                            "total_tokens": 15,
                                        },
                                    )
                                )
                            ]
                        ]
                    ),
                    run_id=run,
                )
                tool = uuid4()
                with ThreadPoolExecutor(max_workers=1) as pool:
                    pool.submit(
                        callbacks[0].on_tool_start,
                        {"name": "lookup"},
                        '{"id":"x"}',
                        run_id=tool,
                    ).result()
                    pool.submit(
                        callbacks[0].on_tool_end,
                        ToolMessage(
                            content='{"status":"ok"}',
                            tool_call_id="t",
                            name="lookup",
                            artifact={"status": "ok", "evidence": []},
                        ),
                        run_id=tool,
                    ).result()
        spans = {s.name: s for s in self.exporter.get_finished_spans()}
        self.assertEqual(
            set(spans),
            {"invoke_agent Account", "agent.graph", "gen_ai.chat", "tool_call lookup"},
        )
        root = spans["invoke_agent Account"]
        graph = spans["agent.graph"]
        self.assertEqual(root.context.trace_id, int("1" * 32, 16))
        self.assertEqual(root.parent.span_id, int("2" * 16, 16))
        self.assertEqual(graph.parent.span_id, root.context.span_id)
        for name in ("gen_ai.chat", "tool_call lookup"):
            span = spans[name]
            self.assertEqual(span.parent.span_id, graph.context.span_id)
            self.assertEqual(span.context.trace_id, root.context.trace_id)
            self.assertEqual(span.attributes["agent.id"], "account-id")
            self.assertEqual(span.attributes["langfuse.session.id"], "session-1")
            self.assertGreaterEqual(span.end_time, span.start_time)
        self.assertEqual(
            spans["gen_ai.chat"].attributes["gen_ai.usage.input_tokens"], 12
        )
        self.assertEqual(
            spans["gen_ai.chat"].attributes["gen_ai.usage.output_tokens"], 3
        )

    def test_tool_failure_and_no_record_business_outcome(self):
        with tracing.agent_span(name="invoke", agent_id="a", protocol="a2a"):
            with tracing.graph_execution("fake") as c:
                run = uuid4()
                c[0].on_tool_start({"name": "missing"}, "{}", run_id=run)
                c[0].on_tool_end(
                    ToolMessage(
                        content="{}",
                        tool_call_id="t",
                        artifact={"status": "customer_not_found", "evidence": []},
                    ),
                    run_id=run,
                )
                bad = uuid4()
                c[0].on_tool_start({"name": "broken"}, "{}", run_id=bad)
                c[0].on_tool_error(ValueError("synthetic failure"), run_id=bad)
        spans = {s.name: s for s in self.exporter.get_finished_spans()}
        self.assertEqual(
            spans["tool_call missing"].attributes["tool.result.status"],
            "customer_not_found",
        )
        self.assertEqual(
            spans["tool_call missing"].status.status_code, StatusCode.UNSET
        )
        self.assertEqual(spans["tool_call broken"].status.status_code, StatusCode.ERROR)

    def test_content_capture_can_be_disabled(self):
        with patch.object(tracing.config, "TRACE_CAPTURE_CONTENT", False):
            with tracing.agent_span(
                name="invoke", agent_id="a", protocol="chat_completions"
            ):
                with tracing.graph_execution("fake") as c:
                    run = uuid4()
                    c[0].on_tool_start({"name": "lookup"}, "PRIVATE_INPUT", run_id=run)
                    c[0].on_tool_end("PRIVATE_OUTPUT", run_id=run)
        attributes = dict(
            next(
                s
                for s in self.exporter.get_finished_spans()
                if s.name == "tool_call lookup"
            ).attributes
        )
        self.assertNotIn("input", attributes)
        self.assertNotIn("output", attributes)
        self.assertNotIn("tool.input", attributes)
        self.assertNotIn("tool.output", attributes)

    def test_graph_failure_records_error_and_closes_unfinished_callback_span(self):
        with self.assertRaisesRegex(ValueError, "graph failure"):
            with tracing.agent_span(name="invoke", agent_id="a", protocol="a2a"):
                with tracing.graph_execution("fake") as c:
                    c[0].on_chat_model_start({}, [], run_id=uuid4())
                    raise ValueError("graph failure")
        spans = self.exporter.get_finished_spans()
        self.assertEqual(len(spans), 3)
        self.assertTrue(all(s.status.status_code == StatusCode.ERROR for s in spans))

    def test_disabled_tracing_does_not_add_callbacks(self):
        with patch.object(tracing, "tracing_enabled", return_value=False):
            with tracing.graph_execution("fake") as callbacks:
                self.assertEqual(callbacks, [])
        self.assertEqual(len(self.exporter.get_finished_spans()), 0)


if __name__ == "__main__":
    unittest.main()
