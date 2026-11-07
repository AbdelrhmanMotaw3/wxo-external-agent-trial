"""Exercise actual API adapters and graph callbacks with a scripted model."""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app import config, graph, tracing
from app.main import app


class ScriptedModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self

    @property
    def _llm_type(self):
        return "offline-scripted-model"

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        m = self._generate(messages, stop=stop).generations[0].message
        yield ChatGenerationChunk(
            message=AIMessageChunk(
                content=m.content,
                tool_calls=m.tool_calls,
                usage_metadata=m.usage_metadata,
            )
        )


class TraceIntegrationTests(unittest.TestCase):
    def test_chat_stream_a2a_and_demo_emit_actual_nested_spans(self):
        collector = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(collector))
        tracer = provider.get_tracer("integration-test")
        usage = {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12}
        fake = ScriptedModel(
            responses=[
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "trial_lookup",
                            "args": {"topic": "account"},
                            "id": "lookup",
                        }
                    ],
                    usage_metadata=usage,
                ),
                AIMessage(content="Offline verified response.", usage_metadata=usage),
            ]
        )
        # Use the original profile in-process; specialists are covered by the
        # subprocess acceptance test. All transport/trace behavior is shared.
        patches = [
            patch.object(graph, "SPECIALIST", None),
            patch.object(graph, "build_llm", return_value=fake),
            patch("app.main.setup_tracing"),
            patch("app.main.shutdown_tracing"),
            patch.object(tracing, "tracing_enabled", return_value=True),
            patch.object(tracing, "get_tracer", return_value=tracer),
            patch.object(tracing.config, "TRACE_CAPTURE_CONTENT", True),
            patch.object(config, "CHAT_AGENT_ID", "chat-id"),
            patch.object(config, "A2A_AGENT_ID", "a2a-id"),
            patch.object(config, "CHAT_OBS_AGENT_ID", "obs-chat-id"),
            patch.object(config, "A2A_OBS_AGENT_ID", "obs-a2a-id"),
            patch.object(config, "AGENT_AUTH_TOKEN", "integration-secret"),
        ]
        for p in patches:
            p.start()
        graph.get_graph.cache_clear()
        headers = {
            "Authorization": "Bearer integration-secret",
            "traceparent": "00-11111111111111111111111111111111-2222222222222222-01",
            "X-IBM-THREAD-ID": "integration-session",
        }
        try:
            with TestClient(app) as client:
                self.assertEqual(client.get("/health").status_code, 200)
                self.assertEqual(
                    client.post("/chat/completions", json={"messages": []}).status_code,
                    401,
                )
                self.assertEqual(len(collector.get_finished_spans()), 0)
                for stream in (False, True):
                    response = client.post(
                        "/chat/completions",
                        headers=headers,
                        json={
                            "messages": [{"role": "user", "content": "lookup account"}],
                            "stream": stream,
                        },
                    )
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertIn("Offline verified response.", response.text)
                response = client.post(
                    "/",
                    headers=headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": "integration",
                        "method": "message/send",
                        "params": {
                            "message": {
                                "messageId": "integration-message",
                                "role": "user",
                                "parts": [{"kind": "text", "text": "lookup account"}],
                            }
                        },
                    },
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(
                    response.json()["result"]["status"]["state"], "completed"
                )
                for path in ("/demo/chat", "/demo/a2a"):
                    response = client.post(
                        path,
                        headers=headers,
                        json={
                            "message": "lookup account",
                            "session_id": "integration-session",
                        },
                    )
                    self.assertEqual(response.status_code, 200, response.text)
            spans = collector.get_finished_spans()
            roots = [
                s
                for s in spans
                if s.name
                in ("chat_completions", "a2a_execute", "demo_chat", "demo_a2a")
            ]
            self.assertEqual(len(roots), 5)
            self.assertEqual(
                {s.attributes["agent.id"] for s in roots},
                {"chat-id", "a2a-id", "obs-chat-id", "obs-a2a-id"},
            )
            self.assertEqual(len([s for s in spans if s.name == "gen_ai.chat"]), 10)
            self.assertEqual(
                len([s for s in spans if s.name == "tool_call trial_lookup"]), 5
            )
            by_id = {s.context.span_id: s for s in spans}
            for span in spans:
                self.assertEqual(span.context.trace_id, int("1" * 32, 16))
                self.assertEqual(
                    span.attributes["langfuse.session.id"], "integration-session"
                )
                self.assertGreaterEqual(span.end_time, span.start_time)
                if span.name == "agent.graph":
                    self.assertIn(by_id[span.parent.span_id], roots)
                if span.name in ("gen_ai.chat", "tool_call trial_lookup"):
                    self.assertEqual(by_id[span.parent.span_id].name, "agent.graph")
                    self.assertLessEqual(
                        span.end_time, by_id[span.parent.span_id].end_time
                    )
                if span.name == "gen_ai.chat":
                    self.assertEqual(span.attributes["gen_ai.usage.total_tokens"], 12)
            self.assertTrue(
                all("input" in s.attributes and "output" in s.attributes for s in roots)
            )
        finally:
            graph.get_graph.cache_clear()
            for p in reversed(patches):
                p.stop()
            provider.shutdown()


if __name__ == "__main__":
    unittest.main()
