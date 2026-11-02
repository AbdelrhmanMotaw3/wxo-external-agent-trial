"""Shared LangGraph ReAct agent backed by OpenRouter."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from app import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a watsonx Orchestrate external-agent trial assistant.
Protocol in use for this turn: {protocol}.
Keep answers short and concrete.
When the user asks for a trial fact, account status, or demo lookup, call the trial_lookup tool.
Mention the protocol name once in your final answer so testers can see which path ran.
"""


@tool
def trial_lookup(topic: str) -> str:
    """Return a fixed demo fact for the given topic. Use for trial / status / lookup questions."""
    normalized = (topic or "").strip().lower()
    catalog = {
        "status": "Trial service is healthy. Hosted on Render, model via OpenRouter.",
        "protocol": "This service supports chat completions and A2A 0.3.0 JSON-RPC.",
        "account": "Demo account ACME-1001 is active with plan External Agents Trial.",
        "observability": "Traces export over OTLP/HTTP to watsonx Orchestrate Agent Analytics.",
    }
    for key, value in catalog.items():
        if key in normalized:
            return value
    return (
        f"No exact match for '{topic}'. Known topics: status, protocol, account, observability."
    )


def build_llm(model: str | None = None) -> ChatOpenAI:
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    return ChatOpenAI(
        model=model or config.OPENROUTER_MODEL,
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL,
        temperature=0,
        streaming=True,
    )


@lru_cache(maxsize=4)
def get_graph(model: str | None = None):
    llm = build_llm(model)
    return create_react_agent(llm, tools=[trial_lookup])


def to_langchain_messages(
    messages: list[dict[str, Any]] | list[Any],
    protocol: str,
) -> list[BaseMessage]:
    converted: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT.format(protocol=protocol))]
    for msg in messages:
        if hasattr(msg, "model_dump"):
            data = msg.model_dump()
        elif isinstance(msg, dict):
            data = msg
        else:
            data = {"role": getattr(msg, "role", "user"), "content": getattr(msg, "content", "")}

        role = (data.get("role") or "user").lower()
        content = data.get("content") or ""
        if role in {"user", "human"}:
            converted.append(HumanMessage(content=content))
        elif role == "system":
            converted.append(SystemMessage(content=content))
        elif role in {"assistant", "ai"}:
            converted.append(AIMessage(content=content))
        elif role == "tool":
            converted.append(
                ToolMessage(
                    content=content,
                    tool_call_id=data.get("tool_call_id") or "unknown",
                    name=data.get("name"),
                )
            )
    return converted


def run_sync(messages: list[Any], protocol: str, model: str | None = None) -> str:
    graph = get_graph(model or config.OPENROUTER_MODEL)
    inputs = {"messages": to_langchain_messages(messages, protocol)}
    result = graph.invoke(inputs)
    last = result["messages"][-1]
    content = getattr(last, "content", "")
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        return "".join(parts)
    return str(content or "")


async def astream_events(messages: list[Any], protocol: str, model: str | None = None):
    graph = get_graph(model or config.OPENROUTER_MODEL)
    inputs = {"messages": to_langchain_messages(messages, protocol)}
    async for event in graph.astream_events(inputs, version="v2"):
        yield event
