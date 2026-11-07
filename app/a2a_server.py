"""A2A 0.3.0 JSON-RPC surface for watsonx Orchestrate."""

from __future__ import annotations

import logging
import asyncio
from typing import Any

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentProvider,
    AgentSkill,
    Part,
    Task,
    TaskState,
    TaskStatus,
)

from app import config
from app.graph import SPECIALIST, run_sync
from app.tracing import agent_span, incoming_request_context, record_content

logger = logging.getLogger(__name__)


def _task_state(name: str) -> Any:
    for candidate in (name, name.lower(), name.upper(), f"TASK_STATE_{name.upper()}"):
        if hasattr(TaskState, candidate):
            return getattr(TaskState, candidate)
    raise AttributeError(f"TaskState has no member matching {name}")


def _text_part(text: str) -> Part:
    try:
        return Part(text=text)  # type: ignore[call-arg]
    except TypeError:
        from a2a.types import TextPart

        return Part(root=TextPart(text=text))


class TrialAgentExecutor(AgentExecutor):
    """Runs the shared LangGraph agent for A2A tasks."""

    def __init__(self, protocol_label: str = "a2a") -> None:
        self.protocol_label = protocol_label
        self.running_tasks: set[str] = set()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id
        if task_id and task_id in self.running_tasks:
            self.running_tasks.remove(task_id)
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task_id or "",
            context_id=context.context_id or "",
        )
        await updater.cancel()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_message = context.message
        task_id = context.task_id
        context_id = context.context_id
        if not user_message or not task_id or not context_id:
            return

        self.running_tasks.add(task_id)
        await event_queue.enqueue_event(
            Task(
                id=task_id,
                context_id=context_id,
                status=TaskStatus(state=_task_state("submitted")),
                history=[user_message],
            )
        )

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task_id,
            context_id=context_id,
        )
        working_message = updater.new_agent_message(
            parts=[_text_part("Working on your trial request...")]
        )
        await updater.start_work(message=working_message)

        query = context.get_user_input()
        try:
            incoming = incoming_request_context()
            with agent_span(
                name="a2a_execute",
                agent_id=config.A2A_AGENT_ID,
                protocol=self.protocol_label,
                session_id=incoming.get("session_id") or context_id,
                carrier=incoming.get("carrier"),
            ) as span:
                if span is not None:
                    span.set_attribute("a2a.task.id", task_id)
                    span.set_attribute("a2a.context.id", context_id)
                record_content(span, "input", query)
                answer = await asyncio.to_thread(run_sync,
                    [{"role": "user", "content": query or ""}],
                    protocol=self.protocol_label,
                )
                record_content(span, "output", answer)
        except Exception as exc:  # noqa: BLE001
            logger.exception("A2A agent execution failed")
            fail_msg = updater.new_agent_message(parts=[_text_part(str(exc))])
            if hasattr(updater, "failed"):
                await updater.failed(message=fail_msg)
            else:
                await updater.complete()
            self.running_tasks.discard(task_id)
            return

        if task_id not in self.running_tasks:
            return

        await updater.add_artifact(
            parts=[_text_part(answer)],
            name="response",
            last_chunk=True,
        )
        await updater.complete()
        self.running_tasks.discard(task_id)


def build_agent_card() -> AgentCard:
    public_url = config.PUBLIC_URL
    skill = AgentSkill(
        id="external_agent_trial",
        name="External Agent Trial",
        description=(
            "Simple LangGraph trial agent for watsonx Orchestrate chat and A2A tests. "
            "Answers short questions and can call a local trial_lookup tool."
        ),
        tags=["trial", "langgraph", "openrouter"],
        examples=[
            "What is the trial account status?",
            "Explain the A2A protocol path.",
            "Lookup observability info.",
        ],
        input_modes=["text"],
        output_modes=["text", "task-status"],
    )
    if SPECIALIST:
        skill = AgentSkill(
            id=config.AGENT_PROFILE,
            name=SPECIALIST.title,
            description=SPECIALIST.description,
            tags=["telecom", "synthetic-data"],
            examples=list(SPECIALIST.examples),
            input_modes=["text"],
            output_modes=["text", "task-status"],
        )
    return AgentCard(
        name=f"{SPECIALIST.title} (A2A)" if SPECIALIST else "External Agent Trial (A2A)",
        description=(
            SPECIALIST.description if SPECIALIST else
            "LangGraph + FastAPI external agent for watsonx Orchestrate A2A 0.3.0 trials. "
            "Route here for A2A protocol tests."
        ),
        provider=AgentProvider(organization="ISYS Trial", url=public_url),
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        default_input_modes=["text"],
        default_output_modes=["text", "task-status"],
        skills=[skill],
        supported_interfaces=[
            AgentInterface(
                protocol_binding="JSONRPC",
                protocol_version="0.3",
                url=public_url,
            ),
            AgentInterface(
                protocol_binding="JSONRPC",
                protocol_version="1.0",
                url=public_url,
            ),
        ],
    )


def build_request_handler(protocol_label: str = "a2a") -> DefaultRequestHandler:
    agent_card = build_agent_card()
    return DefaultRequestHandler(
        agent_executor=TrialAgentExecutor(protocol_label=protocol_label),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )


def mount_a2a_routes(app, protocol_label: str = "a2a") -> None:
    """Attach A2A JSON-RPC and agent-card routes onto an existing FastAPI app."""
    from a2a.server.routes import (
        add_a2a_routes_to_fastapi,
        create_agent_card_routes,
        create_jsonrpc_routes,
    )

    handler = build_request_handler(protocol_label=protocol_label)
    agent_card = build_agent_card()
    jsonrpc_routes = create_jsonrpc_routes(
        request_handler=handler,
        rpc_url="/",
        enable_v0_3_compat=True,
    )
    agent_card_routes = create_agent_card_routes(agent_card=agent_card)
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=agent_card_routes,
        jsonrpc_routes=jsonrpc_routes,
    )
    logger.info("Mounted A2A JSON-RPC at / and agent card at /.well-known/agent-card.json")
