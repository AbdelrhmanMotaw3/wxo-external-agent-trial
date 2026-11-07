"""Observe LangChain model/tool callbacks without changing agent decisions."""

from __future__ import annotations

from threading import Lock

from langchain_core.callbacks import BaseCallbackHandler
from opentelemetry.trace import SpanKind

from app.tracing import mark_error, record_content


class AgentTraceCallback(BaseCallbackHandler):
    run_inline = True
    raise_error = False

    def __init__(self, tracer, parent, identity, model):
        self.tracer = tracer
        self.parent = parent
        self.identity = dict(identity)
        self.model = model
        self.spans = {}
        self.lock = Lock()

    def _start(self, run_id, name, attributes):
        span = self.tracer.start_span(
            name,
            context=self.parent,
            kind=SpanKind.INTERNAL,
            attributes={**self.identity, **attributes},
        )
        with self.lock:
            self.spans[run_id] = span
        return span

    def _finish(self, run_id):
        with self.lock:
            return self.spans.pop(run_id, None)

    def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs):
        params = kwargs.get("invocation_params") or {}
        model = params.get("model") or params.get("model_name") or self.model
        span = self._start(
            run_id,
            "gen_ai.chat",
            {
                "gen_ai.operation.name": "chat",
                "gen_ai.system": "openrouter",
                "gen_ai.provider.name": "openrouter",
                "gen_ai.request.model": str(model),
            },
        )
        record_content(
            span,
            "input",
            [
                [{"role": getattr(m, "type", ""), "content": m.content} for m in batch]
                for batch in messages
            ],
        )

    def on_llm_start(self, serialized, prompts, *, run_id, **kwargs):
        span = self._start(
            run_id,
            "gen_ai.chat",
            {
                "gen_ai.operation.name": "chat",
                "gen_ai.system": "openrouter",
                "gen_ai.request.model": self.model,
            },
        )
        record_content(span, "input", prompts)

    def on_llm_end(self, response, *, run_id, **kwargs):
        span = self._finish(run_id)
        if span is None:
            return
        try:
            outputs = []
            totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            has_usage = False
            for batch in response.generations:
                for generation in batch:
                    message = getattr(generation, "message", None)
                    outputs.append(
                        getattr(message, "content", getattr(generation, "text", ""))
                    )
                    metadata = getattr(message, "response_metadata", {}) or {}
                    if metadata.get("model_name") or metadata.get("model"):
                        span.set_attribute(
                            "gen_ai.response.model",
                            str(metadata.get("model_name") or metadata["model"]),
                        )
                    usage = getattr(message, "usage_metadata", None)
                    if usage:
                        has_usage = True
                        for key in totals:
                            totals[key] += int(usage.get(key, 0) or 0)
                    calls = getattr(message, "tool_calls", None)
                    if calls:
                        record_content(span, "gen_ai.tool_calls", calls)
            if not has_usage:
                usage = (response.llm_output or {}).get("token_usage") or (
                    response.llm_output or {}
                ).get("usage")
                if usage:
                    has_usage = True
                    totals = {
                        "input_tokens": int(
                            usage.get("prompt_tokens", usage.get("input_tokens", 0))
                            or 0
                        ),
                        "output_tokens": int(
                            usage.get(
                                "completion_tokens", usage.get("output_tokens", 0)
                            )
                            or 0
                        ),
                        "total_tokens": int(usage.get("total_tokens", 0) or 0),
                    }
            if has_usage:
                for key, value in totals.items():
                    span.set_attribute("gen_ai.usage." + key, value)
                span.set_attribute("gen_ai.usage.source", "provider")
            record_content(span, "output", outputs)
        finally:
            span.end()

    def on_llm_error(self, error, *, run_id, **kwargs):
        span = self._finish(run_id)
        if span is not None:
            mark_error(span, error)
            span.end()

    def on_tool_start(self, serialized, input_str, *, run_id, inputs=None, **kwargs):
        name = (serialized or {}).get("name") or kwargs.get("name") or "tool"
        span = self._start(
            run_id,
            "tool_call " + name,
            {
                "gen_ai.operation.name": "execute_tool",
                "tool.name": name,
                "gen_ai.tool.name": name,
            },
        )
        value = inputs if inputs is not None else input_str
        record_content(span, "input", value)
        record_content(span, "tool.input", value)

    def on_tool_end(self, output, *, run_id, **kwargs):
        span = self._finish(run_id)
        if span is None:
            return
        try:
            record_content(span, "output", getattr(output, "content", output))
            record_content(span, "tool.output", getattr(output, "content", output))
            artifact = getattr(output, "artifact", None)
            if isinstance(artifact, dict) and artifact.get("status"):
                span.set_attribute("tool.result.status", str(artifact["status"]))
                span.set_attribute(
                    "tool.business_outcome",
                    "success"
                    if artifact["status"] == "ok"
                    else "no_match_or_unavailable",
                )
            if getattr(output, "status", None) == "error":
                mark_error(span, RuntimeError("Tool returned an error"))
        finally:
            span.end()

    def on_tool_error(self, error, *, run_id, **kwargs):
        span = self._finish(run_id)
        if span is not None:
            mark_error(span, error)
            span.end()

    def close(self, error=None):
        with self.lock:
            pending = list(self.spans.values())
            self.spans.clear()
        for span in pending:
            mark_error(
                span,
                error or RuntimeError("Execution ended before callback completion"),
            )
            span.end()
