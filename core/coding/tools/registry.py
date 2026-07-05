"""Core coding tool registry."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from core.coding.tools.base import RegisteredTool, ToolResult
from core.coding.tools.schemas import (
    AgentArgs,
    EnterPlanModeArgs,
    ExitPlanModeArgs,
    ListFilesArgs,
    PatchFileArgs,
    ReadFileArgs,
    RunShellArgs,
    SearchArgs,
    SendMessageArgs,
    TaskStopArgs,
    TodoAddArgs,
    TodoListArgs,
    TodoUpdateArgs,
    WriteFileArgs,
    first_error_message,
)
from core.coding.workspace import IGNORED_PATH_NAMES, WorkspaceContext, clip

ALLOWED_SHELL_ENV = {
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "PYTHONPATH",
    "CONDA_DEFAULT_ENV",
    "CONDA_PREFIX",
    "VIRTUAL_ENV",
}

TOOL_SPECS: dict[str, dict[str, Any]] = {
    "list_files": {
        "schema": {"path": "str='.'"},
        "description": "List files in the workspace.",
        "risky": False,
    },
    "read_file": {
        "schema": {"path": "str", "start": "int=1", "end": "int=200"},
        "description": "Read a UTF-8 file by line range.",
        "risky": False,
    },
    "search": {
        "schema": {"pattern": "str", "path": "str='.'"},
        "description": "Search the workspace using rg or a Python fallback.",
        "risky": False,
    },
    "run_shell": {
        "schema": {"command": "str", "timeout": "int=20"},
        "description": "Run a shell command in the workspace root.",
        "risky": True,
    },
    "write_file": {
        "schema": {"path": "str", "content": "str"},
        "description": "Write a text file.",
        "risky": True,
    },
    "patch_file": {
        "schema": {"path": "str", "old_text": "str", "new_text": "str"},
        "description": "Replace one exact text block in a file.",
        "risky": True,
    },
    "todo_add": {
        "schema": {
            "content": "str",
            "status": "str='pending'",
            "priority": "str='normal'",
            "note": "str=''",
        },
        "description": "Add an item to the session task ledger.",
        "risky": False,
    },
    "todo_update": {
        "schema": {
            "todo_id": "str",
            "status": "str?",
            "content": "str?",
            "priority": "str?",
            "note": "str?",
        },
        "description": "Update an item in the session task ledger.",
        "risky": False,
    },
    "todo_list": {
        "schema": {},
        "description": "List the session task ledger.",
        "risky": False,
    },
    "enter_plan_mode": {
        "schema": {"topic": "str", "path": "str?"},
        "description": "Enter plan mode for a named planning topic.",
        "risky": False,
    },
    "exit_plan_mode": {
        "schema": {},
        "description": "Exit plan mode and return to default mode.",
        "risky": False,
    },
    "agent": {
        "schema": {
            "description": "str",
            "prompt": "str",
            "subagent_type": "str='worker'",
            "write_scope": "list[str]=[]",
        },
        "description": "Launch a bounded worker or read-only Explore subagent.",
        "risky": False,
    },
    "send_message": {
        "schema": {"to": "str", "message": "str"},
        "description": "Continue an existing worker by id.",
        "risky": False,
    },
    "task_stop": {
        "schema": {"task_id": "str"},
        "description": "Stop a worker by id.",
        "risky": False,
    },
}

SCHEMAS: dict[str, type[BaseModel]] = {
    "list_files": ListFilesArgs,
    "read_file": ReadFileArgs,
    "search": SearchArgs,
    "run_shell": RunShellArgs,
    "write_file": WriteFileArgs,
    "patch_file": PatchFileArgs,
    "todo_add": TodoAddArgs,
    "todo_update": TodoUpdateArgs,
    "todo_list": TodoListArgs,
    "enter_plan_mode": EnterPlanModeArgs,
    "exit_plan_mode": ExitPlanModeArgs,
    "agent": AgentArgs,
    "send_message": SendMessageArgs,
    "task_stop": TaskStopArgs,
}


@dataclass
class ToolContext:
    """Optional runtime components used by extended tools."""

    runtime: Any | None = None
    todo_ledger: Any | None = None
    worker_manager: Any | None = None


def build_tool_registry(
    workspace: WorkspaceContext,
    tool_context: ToolContext | None = None,
) -> dict[str, RegisteredTool]:
    """Build coding tools for one workspace."""

    def make_runner(name: str) -> Any:
        def runner(args: dict[str, Any]) -> ToolResult | str:
            return execute_tool(workspace, name, args, tool_context=tool_context)

        return runner

    return {
        name: RegisteredTool(
            name=name,
            schema=dict(spec["schema"]),
            description=str(spec["description"]),
            risky=bool(spec["risky"]),
            runner=make_runner(name),
        )
        for name, spec in TOOL_SPECS.items()
    }


def execute_tool(
    workspace: WorkspaceContext,
    name: str,
    args: dict[str, Any] | None,
    tool_context: ToolContext | None = None,
) -> ToolResult:
    """Validate and execute one registered tool."""
    validated = validate_tool(workspace, name, args or {})
    runner = TOOL_RUNNERS.get(name)
    if runner is None:
        return ToolResult(content=f"unknown tool: {name}", is_error=True)
    if name in EXTENDED_TOOL_RUNNERS:
        return EXTENDED_TOOL_RUNNERS[name](tool_context, validated)
    return runner(workspace, validated)


def validate_tool(
    workspace: WorkspaceContext,
    name: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Validate pydantic schema and workspace-aware constraints."""
    schema_cls = SCHEMAS.get(name)
    if schema_cls is None:
        raise ValueError(f"unknown tool: {name}")
    try:
        validated = schema_cls.model_validate(args).model_dump()
    except ValidationError as exc:
        raise ValueError(first_error_message(exc)) from exc

    if name == "list_files":
        path = workspace.path(str(validated["path"]))
        if not path.is_dir():
            raise ValueError("path is not a directory")
    elif name == "read_file":
        path = workspace.path(str(validated["path"]))
        if not path.is_file():
            raise ValueError("path is not a file")
    elif name == "search":
        workspace.path(str(validated["path"]))
    elif name == "write_file":
        path = workspace.path(str(validated["path"]))
        if path.exists() and path.is_dir():
            raise ValueError("path is a directory")
    elif name == "patch_file":
        path = workspace.path(str(validated["path"]))
        if not path.is_file():
            raise ValueError("path is not a file")
        old_text = str(validated["old_text"])
        text = path.read_text(encoding="utf-8", errors="replace")
        count = text.count(old_text)
        if count != 1:
            raise ValueError(f"old_text must occur exactly once, found {count}")
    return validated


def tool_list_files(workspace: WorkspaceContext, args: dict[str, Any]) -> ToolResult:
    """List workspace files with stable markers."""
    path = workspace.path(str(args.get("path", ".")))
    entries = [
        item
        for item in sorted(path.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
        if item.name not in IGNORED_PATH_NAMES
    ]
    lines = [
        f"{'[D]' if entry.is_dir() else '[F]'} {entry.relative_to(workspace.root)}"
        for entry in entries[:200]
    ]
    return ToolResult(content="\n".join(lines) or "(empty)")


def tool_read_file(workspace: WorkspaceContext, args: dict[str, Any]) -> ToolResult:
    """Read a UTF-8 text file by line range."""
    path = workspace.path(str(args["path"]))
    start = int(args.get("start", 1))
    end = int(args.get("end", 200))
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    body = "\n".join(
        f"{number:>4}: {line}" for number, line in enumerate(lines[start - 1 : end], start=start)
    )
    workspace.mark_read(path)
    return ToolResult(content=clip(f"# {path.relative_to(workspace.root)}\n{body}"))


def tool_search(workspace: WorkspaceContext, args: dict[str, Any]) -> ToolResult:
    """Search for a pattern under the workspace."""
    pattern = str(args["pattern"])
    path = workspace.path(str(args.get("path", ".")))

    if shutil.which("rg"):
        target = "." if path == workspace.root else str(path.relative_to(workspace.root))
        result = subprocess.run(
            ["rg", "-n", "--smart-case", "--max-count", "200", pattern, target],
            cwd=workspace.root,
            capture_output=True,
            text=True,
            check=False,
        )
        content = result.stdout.strip() or result.stderr.strip() or "(no matches)"
        return ToolResult(content=clip(content))

    matches: list[str] = []
    files = [path] if path.is_file() else _walk_search_files(path, workspace.root)
    for file_path in files:
        for number, line in enumerate(
            file_path.read_text(encoding="utf-8", errors="replace").splitlines(),
            start=1,
        ):
            if pattern.lower() in line.lower():
                matches.append(f"{file_path.relative_to(workspace.root)}:{number}:{line}")
                if len(matches) >= 200:
                    return ToolResult(content=clip("\n".join(matches)))
    return ToolResult(content=clip("\n".join(matches) or "(no matches)"))


def tool_run_shell(workspace: WorkspaceContext, args: dict[str, Any]) -> ToolResult:
    """Run a shell command with timeout and filtered environment."""
    command = str(args["command"])
    timeout = int(args.get("timeout", 20))
    try:
        result = subprocess.run(
            command,
            cwd=workspace.root,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_filtered_env(),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(content=f"command timed out after {timeout}s", is_error=True)
    content = textwrap.dedent(
        f"""\
        exit_code: {result.returncode}
        stdout:
        {result.stdout.strip() or "(empty)"}
        stderr:
        {result.stderr.strip() or "(empty)"}
        """
    ).strip()
    return ToolResult(content=clip(content), is_error=result.returncode != 0)


def tool_write_file(workspace: WorkspaceContext, args: dict[str, Any]) -> ToolResult:
    """Write a text file under the workspace."""
    path = workspace.path(str(args["path"]))
    content = str(args["content"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    workspace.mark_self_authored(path)
    return ToolResult(content=f"wrote {path.relative_to(workspace.root)} ({len(content)} chars)")


def tool_patch_file(workspace: WorkspaceContext, args: dict[str, Any]) -> ToolResult:
    """Replace one exact text block in a file."""
    path = workspace.path(str(args["path"]))
    old_text = str(args["old_text"])
    new_text = str(args["new_text"])
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace(old_text, new_text, 1), encoding="utf-8")
    workspace.mark_self_authored(path)
    return ToolResult(content=f"patched {path.relative_to(workspace.root)}")


def _walk_search_files(path: Path, root: Path) -> list[Path]:
    return [
        item
        for item in path.rglob("*")
        if item.is_file()
        and not any(part in IGNORED_PATH_NAMES for part in item.relative_to(root).parts)
    ]


def _filtered_env() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if key in ALLOWED_SHELL_ENV}


TOOL_RUNNERS = {
    "list_files": tool_list_files,
    "read_file": tool_read_file,
    "search": tool_search,
    "run_shell": tool_run_shell,
    "write_file": tool_write_file,
    "patch_file": tool_patch_file,
}


def tool_todo_add(context: ToolContext | None, args: dict[str, Any]) -> ToolResult:
    ledger = _require_context_attr(context, "todo_ledger")
    item = ledger.add(
        str(args["content"]),
        status=str(args.get("status", "pending")),
        priority=str(args.get("priority", "normal")),
        note=str(args.get("note", "")),
    )
    return ToolResult(
        content=f"added {item['id']} [{item['status']}] {item['priority']} - {item['content']}"
    )


def tool_todo_update(context: ToolContext | None, args: dict[str, Any]) -> ToolResult:
    ledger = _require_context_attr(context, "todo_ledger")
    item = ledger.update(
        str(args["todo_id"]),
        status=args.get("status"),
        content=args.get("content"),
        priority=args.get("priority"),
        note=args.get("note"),
    )
    return ToolResult(
        content=f"updated {item['id']} [{item['status']}] {item['priority']} - {item['content']}"
    )


def tool_todo_list(context: ToolContext | None, args: dict[str, Any]) -> ToolResult:
    _ = args
    ledger = _require_context_attr(context, "todo_ledger")
    return ToolResult(content=str(ledger.render_list()))


def tool_enter_plan_mode(context: ToolContext | None, args: dict[str, Any]) -> ToolResult:
    runtime = _require_context_attr(context, "runtime")
    path = runtime.enter_plan_mode(str(args["topic"]), path=args.get("path"))
    return ToolResult(content=f"mode: plan\nplan path: {path}")


def tool_exit_plan_mode(context: ToolContext | None, args: dict[str, Any]) -> ToolResult:
    _ = args
    runtime = _require_context_attr(context, "runtime")
    runtime.exit_plan_mode()
    return ToolResult(content="mode: default")


def tool_agent(context: ToolContext | None, args: dict[str, Any]) -> ToolResult:
    manager = _require_context_attr(context, "worker_manager")
    payload = manager.spawn(
        description=str(args["description"]),
        prompt=str(args["prompt"]),
        subagent_type=str(args.get("subagent_type", "worker")),
        write_scope=args.get("write_scope", []),
    )
    return ToolResult(content=json.dumps(payload, ensure_ascii=False, sort_keys=True))


def tool_send_message(context: ToolContext | None, args: dict[str, Any]) -> ToolResult:
    manager = _require_context_attr(context, "worker_manager")
    payload = manager.send_message(str(args["to"]), str(args["message"]))
    return ToolResult(content=json.dumps(payload, ensure_ascii=False, sort_keys=True))


def tool_task_stop(context: ToolContext | None, args: dict[str, Any]) -> ToolResult:
    manager = _require_context_attr(context, "worker_manager")
    payload = manager.stop(str(args["task_id"]))
    return ToolResult(content=json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _require_context_attr(context: ToolContext | None, attr: str) -> Any:
    value = getattr(context, attr, None) if context is not None else None
    if value is None:
        raise ValueError(f"{attr} is not configured")
    return value


EXTENDED_TOOL_RUNNERS = {
    "todo_add": tool_todo_add,
    "todo_update": tool_todo_update,
    "todo_list": tool_todo_list,
    "enter_plan_mode": tool_enter_plan_mode,
    "exit_plan_mode": tool_exit_plan_mode,
    "agent": tool_agent,
    "send_message": tool_send_message,
    "task_stop": tool_task_stop,
}
