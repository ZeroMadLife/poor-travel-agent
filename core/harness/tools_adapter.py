"""Expose a bounded, read-only slice of Sage coding tools to LangChain."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from core.coding.engine.events import ToolResultEvent, event_to_dict
from core.coding.runtime import CodingRuntime
from core.coding.tool_executor.executor import ToolExecutor

_DEERFLOW_TOOLS = frozenset(
    {"list_files", "read_file", "search", "write_file", "patch_file", "run_shell"}
)


def build_deerflow_coding_tools(runtime: CodingRuntime, *, run_id: str) -> list[BaseTool]:
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
            return result or f"{_name} completed without a result"

        tools.append(
            StructuredTool.from_function(
                coroutine=invoke,
                name=name,
                description=registered.description,
                args_schema=definition.schema_model,
            )
        )
    return tools


def _stream_writer() -> Callable[[Any], None] | None:
    try:
        from langgraph.config import get_stream_writer

        return get_stream_writer()
    except (KeyError, RuntimeError):
        return None


__all__ = ["build_deerflow_coding_tools"]
