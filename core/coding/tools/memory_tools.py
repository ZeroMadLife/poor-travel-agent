"""Memory tools for the coding agent.

``remember`` persists a fact to durable workspace memory. ``dream`` generates
memory consolidation proposals for the user to review (proposal-only, no
mutation). Both tools are deferred: they are activated via ``tool_search`` so
they do not consume the model's resident tool budget by default.
"""

from __future__ import annotations

from typing import Any

from core.coding.context import WorkspaceContext
from core.coding.tools.base import ToolContext, ToolResult
from core.coding.tools.registry import register_tool
from core.coding.tools.schemas import DreamArgs, RememberArgs


@register_tool(
    name="remember",
    description="Save a fact to durable workspace memory.",
    schema={"fact": "str", "topic": "str='project-conventions'"},
    schema_model=RememberArgs,
    risky=False,
    category="memory",
    deferred=True,
)
def remember(
    workspace: WorkspaceContext,
    args: dict[str, Any],
    tool_context: ToolContext | None = None,
) -> ToolResult:
    _ = workspace
    runtime = _require_context_attr(tool_context, "runtime")
    fact = runtime.memory_manager.remember(
        str(args["fact"]), topic=str(args.get("topic", "project-conventions"))
    )
    return ToolResult(content=f"Remembered: {fact.content} (topic: {fact.topic})")


@register_tool(
    name="dream",
    description="Generate memory consolidation proposals for review.",
    schema={"topic": "str?"},
    schema_model=DreamArgs,
    risky=False,
    category="memory",
    deferred=True,
)
def dream(
    workspace: WorkspaceContext,
    args: dict[str, Any],
    tool_context: ToolContext | None = None,
) -> ToolResult:
    _ = workspace, args
    runtime = _require_context_attr(tool_context, "runtime")
    proposals = runtime.memory_manager.propose_dream()
    if not proposals:
        return ToolResult(content="No facts to consolidate.")
    lines = ["Memory proposals (awaiting approval):"]
    for p in proposals:
        lines.append(f"- [{p.topic}] {p.content}")
    return ToolResult(content="\n".join(lines))


def _require_context_attr(context: ToolContext | None, attr: str) -> Any:
    value = getattr(context, attr, None) if context is not None else None
    if value is None:
        raise ValueError(f"{attr} is not configured")
    return value
