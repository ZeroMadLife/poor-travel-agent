"""Worker runtime assembly for coding subagents."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.coding.context_manager import ContextManager
from core.coding.engine import Engine
from core.coding.permissions import PermissionChecker
from core.coding.tool_policy import ToolPolicyChecker
from core.coding.tools.registry import build_tool_registry
from core.coding.worker_execution import WorkerTask
from core.coding.workspace import WorkspaceContext


async def run_worker_task(
    task: WorkerTask,
    workspace: WorkspaceContext,
    model_factory: Callable[[], Any],
) -> str:
    """Run one worker task and return its final response."""
    tools = build_tool_registry(workspace)
    permission = PermissionChecker(
        approval_policy="auto",
        write_scope=task.write_scope,
        plan_mode=task.subagent_type == "Explore",
    )
    engine = Engine(
        model=model_factory(),
        workspace=workspace,
        tools=tools,
        context_manager=ContextManager(),
        permission_checker=permission,
        policy_checker=ToolPolicyChecker(workspace),
        max_steps=20,
    )
    final = ""
    async for event in engine.run_turn(task.prompt):
        if event["type"] == "final":
            final = str(event["content"])
    return final
