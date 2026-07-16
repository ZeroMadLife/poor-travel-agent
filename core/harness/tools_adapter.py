"""Expose a bounded, read-only slice of Sage coding tools to LangChain."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from core.coding.runtime import CodingRuntime
from core.coding.tools.base import RegisteredTool

_DEERFLOW_READ_TOOLS = frozenset({"list_files", "read_file", "search"})


def build_deerflow_read_tools(runtime: CodingRuntime) -> list[BaseTool]:
    """Build LangChain tools while keeping Sage validation and workspace guards."""
    tools: list[BaseTool] = []
    from core.coding.tools.registry import registered_tool_definitions

    definitions = registered_tool_definitions()
    for name in sorted(_DEERFLOW_READ_TOOLS):
        registered = runtime.tools.get(name)
        definition = definitions.get(name)
        if registered is None or definition is None:
            continue

        bound_registered = registered

        def invoke(_registered: RegisteredTool = bound_registered, **kwargs: Any) -> str:
            return str(_registered.execute(dict(kwargs)).content)

        tools.append(
            StructuredTool.from_function(
                func=invoke,
                name=name,
                description=registered.description,
                args_schema=definition.schema_model,
            )
        )
    return tools


__all__ = ["build_deerflow_read_tools"]
