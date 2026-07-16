"""Expose a bounded, read-only slice of Sage coding tools to LangChain."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from sage_harness import MemoryPort

from core.coding.engine.events import ToolResultEvent, event_to_dict
from core.coding.runtime import CodingRuntime
from core.coding.tool_executor.executor import ToolExecutor

_DEERFLOW_TOOLS = frozenset(
    {"list_files", "read_file", "search", "write_file", "patch_file", "run_shell", "agent"}
)


def build_deerflow_coding_tools(
    runtime: CodingRuntime,
    *,
    run_id: str,
    memory_port: MemoryPort | None = None,
) -> list[BaseTool]:
    """Build LangChain tools through Sage's existing executor and approval gate."""
    tools: list[BaseTool] = []
    from core.coding.tools.registry import registered_tool_definitions

    definitions = registered_tool_definitions()
    for name in sorted(_DEERFLOW_TOOLS):
        registered = runtime.tools.get(name)
        definition = definitions.get(name)
        if registered is None or definition is None:
            continue

        bound_name = name

        async def invoke(_name: str = bound_name, **kwargs: Any) -> str:
            executor = ToolExecutor(
                tools=runtime.tools,
                workspace=runtime.workspace,
                permission_checker=runtime.permission_checker,
                policy_checker=runtime.policy_checker,
                approval_manager=runtime.approval_manager,
                session_id=runtime.session_id,
                should_stop=lambda: runtime.stop_requested,
                run_id=run_id,
            )
            result = ""
            writer = _stream_writer()
            async for event in executor.execute({"name": _name, "args": dict(kwargs)}):
                payload = event_to_dict(event)
                if writer is not None:
                    writer(payload)
                if isinstance(event, ToolResultEvent):
                    result = event.content
                    if _name == "agent" and writer is not None:
                        agent_event = _agent_started_event(result)
                        if agent_event is not None:
                            writer(agent_event)
            return result or f"{_name} completed without a result"

        tools.append(
            StructuredTool.from_function(
                coroutine=invoke,
                name=name,
                description=registered.description,
                args_schema=definition.schema_model,
            )
        )
    if memory_port is not None:
        remember_definition = definitions.get("remember")
        if remember_definition is not None:

            async def propose_memory(
                fact: str,
                topic: str = "project-conventions",
            ) -> str:
                receipt = await memory_port.propose(
                    runtime.session_id,
                    run_id,
                    fact,
                    topic=topic,
                )
                return json.dumps(
                    {
                        "proposal_id": receipt.proposal_id,
                        "status": receipt.status,
                        "requires_user_confirmation": receipt.status == "pending",
                        "session_id": receipt.thread_id,
                        "run_id": receipt.run_id,
                        "reflection_id": receipt.reflection_id,
                        "candidate_count": receipt.candidate_count,
                        "base_revision": receipt.base_revision,
                    },
                    ensure_ascii=True,
                )

            tools.append(
                StructuredTool.from_function(
                    coroutine=propose_memory,
                    name="remember",
                    description=(
                        "Propose a stable workspace convention or decision for user review. "
                        "This tool never writes durable memory until the proposal is approved."
                    ),
                    args_schema=remember_definition.schema_model,
                )
            )
    return tools


def _stream_writer() -> Callable[[Any], None] | None:
    try:
        from langgraph.config import get_stream_writer

        return get_stream_writer()
    except (KeyError, RuntimeError):
        return None


def _agent_started_event(content: str) -> dict[str, Any] | None:
    """Project a worker launch into a small public event, never its full trace."""
    import json

    try:
        payload = json.loads(content)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict) or not str(payload.get("task_id", "")).strip():
        return None
    return {
        "type": "agent_started",
        "agent_run_id": str(payload["task_id"]),
        "status": str(payload.get("status", "started")),
        "description": str(payload.get("description", ""))[:400],
    }


__all__ = ["build_deerflow_coding_tools"]
