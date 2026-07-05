"""Async generator engine for one coding-agent turn."""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator
from typing import Any, Protocol

from core.coding.context_manager import ContextManager
from core.coding.engine_helpers import (
    build_tool_descriptions,
    normalize_tool_payload,
    step_limit_summary,
)
from core.coding.model_output import parse
from core.coding.permissions import PermissionChecker
from core.coding.tool_policy import ToolPolicyChecker
from core.coding.tools.base import RegisteredTool, ToolResult
from core.coding.workspace import WorkspaceContext, now


class ModelClient(Protocol):
    """Minimal model contract used by the coding engine."""

    async def complete(self, prompt: str) -> str:
        """Return raw model text."""
        ...


class Engine:
    """Turn control loop: model -> parse -> tool -> final."""

    def __init__(
        self,
        model: Any,
        workspace: WorkspaceContext,
        tools: dict[str, RegisteredTool],
        context_manager: ContextManager,
        permission_checker: PermissionChecker,
        policy_checker: ToolPolicyChecker,
        history: list[dict[str, Any]] | None = None,
        max_steps: int = 50,
    ) -> None:
        self.model = model
        self.workspace = workspace
        self.tools = tools
        self.context_manager = context_manager
        self.permission_checker = permission_checker
        self.policy_checker = policy_checker
        self.history = history if history is not None else []
        self.max_steps = max_steps

    async def run_turn(self, user_message: str) -> AsyncIterator[dict[str, Any]]:
        """Run one coding turn and yield streamable events."""
        self.history.append({"role": "user", "content": user_message, "created_at": now()})
        tool_steps = 0
        attempts = 0

        while tool_steps < self.max_steps and attempts < self.max_steps + 2:
            attempts += 1
            prompt, metadata = self.context_manager.build(
                user_message=user_message,
                history=self.history,
                tools=self._tool_descriptions(),
            )
            yield {
                "type": "model_requested",
                "attempts": attempts,
                "tool_steps": tool_steps,
                "prompt_chars": metadata["prompt_chars"],
            }

            raw = await self._call_model(prompt)
            kind, payload = parse(raw)
            yield {"type": "model_parsed", "kind": kind}

            if kind in {"tool", "tools"}:
                tool_payloads = [payload] if kind == "tool" else list(payload)
                for tool_payload in tool_payloads:
                    if tool_steps >= self.max_steps:
                        break
                    async for event in self._execute_tool_payload(tool_payload):
                        yield event
                    tool_steps += 1
                continue

            if kind == "retry":
                notice = str(payload)
                self.history.append({"role": "assistant", "content": notice, "created_at": now()})
                yield {"type": "retry", "content": notice}
                continue

            final = str(payload).strip()
            self.history.append({"role": "assistant", "content": final, "created_at": now()})
            yield {"type": "final", "content": final}
            return

        content = self._step_limit_summary(user_message, tool_steps)
        self.history.append({"role": "assistant", "content": content, "created_at": now()})
        yield {"type": "step_limit", "content": content}

    async def _execute_tool_payload(self, payload: Any) -> AsyncIterator[dict[str, Any]]:
        name, args = normalize_tool_payload(payload)
        tool = self.tools.get(name)
        if tool is None:
            result = ToolResult(content=f"unknown tool: {name}", is_error=True)
            yield self._tool_result_event(name, args, result)
            return

        permission = self.permission_checker.check(tool, args, self.workspace)
        if not permission.allowed:
            result = ToolResult(content=permission.reason, is_error=True)
            event = self._tool_result_event(name, args, result)
            event["security_event_type"] = permission.security_event_type
            yield event
            return

        policy = self.policy_checker.check(tool, args)
        if not policy.allowed:
            result = ToolResult(content=policy.message, is_error=True)
            event = self._tool_result_event(name, args, result)
            event["policy_reason"] = policy.reason
            yield event
            return

        yield {"type": "tool_call", "tool": name, "args": args}
        result = tool.execute(args)
        yield self._tool_result_event(name, args, result)

    def _tool_result_event(
        self,
        name: str,
        args: dict[str, Any],
        result: ToolResult,
    ) -> dict[str, Any]:
        self.history.append(
            {
                "role": "tool",
                "name": name,
                "args": args,
                "content": result.content,
                "is_error": result.is_error,
                "created_at": now(),
            }
        )
        return {
            "type": "tool_result",
            "tool": name,
            "args": args,
            "content": result.content,
            "is_error": result.is_error,
        }

    async def _call_model(self, prompt: str) -> str:
        complete = getattr(self.model, "complete", None)
        if callable(complete):
            result = complete(prompt)
            if inspect.isawaitable(result):
                value = await result
            else:
                value = result
            return str(value)

        ainvoke = getattr(self.model, "ainvoke", None)
        if callable(ainvoke):
            response = await ainvoke([{"role": "user", "content": prompt}])
            content = getattr(response, "content", response)
            return content if isinstance(content, str) else str(content)
        raise TypeError("model must provide complete(prompt) or ainvoke(messages)")

    def _tool_descriptions(self) -> list[str]:
        return build_tool_descriptions(self.tools)

    @staticmethod
    def _step_limit_summary(user_message: str, tool_steps: int) -> str:
        return step_limit_summary(user_message, tool_steps)
