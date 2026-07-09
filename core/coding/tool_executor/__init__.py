"""Tool execution and permission-governance public API."""

from core.coding.tool_executor.approval import (
    ApprovalEntry,
    ApprovalManager,
    check_dangerous_command,
)
from core.coding.tool_executor.permissions import (
    ApprovalCallback,
    PermissionChecker,
    PermissionDecision,
    PermissionMode,
)
from core.coding.tool_executor.policy import ToolPolicyChecker, ToolPolicyDecision

__all__ = [
    "ApprovalCallback",
    "ApprovalEntry",
    "ApprovalManager",
    "PermissionChecker",
    "PermissionDecision",
    "PermissionMode",
    "ToolExecutor",
    "ToolPolicyChecker",
    "ToolPolicyDecision",
    "check_dangerous_command",
]


def __getattr__(name: str) -> object:
    """Lazily expose ToolExecutor to avoid cycles with engine events."""
    if name == "ToolExecutor":
        from core.coding.tool_executor.executor import ToolExecutor

        return ToolExecutor
    raise AttributeError(name)
