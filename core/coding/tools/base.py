"""Tool abstraction for the coding agent."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolResult:
    """Result returned by a coding tool."""

    content: str
    is_error: bool = False


ToolRunner = Callable[[dict[str, Any]], ToolResult | str]


@dataclass(frozen=True)
class RegisteredTool:
    """A registered coding tool with schema, risk, and executable runner."""

    name: str
    schema: dict[str, Any]
    description: str
    risky: bool
    runner: ToolRunner

    @property
    def read_only(self) -> bool:
        """Return whether this tool is safe to run without write approval."""
        return not self.risky

    def execute(self, args: dict[str, Any] | None = None) -> ToolResult:
        """Execute the tool and convert validation/runtime failures to ToolResult."""
        try:
            result = self.runner(args or {})
        except Exception as exc:
            return ToolResult(content=str(exc), is_error=True)
        if isinstance(result, ToolResult):
            return result
        return ToolResult(content=str(result))
