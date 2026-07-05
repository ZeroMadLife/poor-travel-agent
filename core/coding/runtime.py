"""Runtime assembly for a web coding-agent session."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

from core.coding.context_manager import ContextManager
from core.coding.engine import Engine
from core.coding.permissions import PermissionChecker
from core.coding.plan_mode import PlanModeManager
from core.coding.run_store import RunStore
from core.coding.session_events import SessionEventBus
from core.coding.session_store import CodingSessionStore
from core.coding.todo_ledger import TodoLedger
from core.coding.tool_policy import ToolPolicyChecker
from core.coding.tools.registry import ToolContext, build_tool_registry
from core.coding.worker_manager import WorkerManager
from core.coding.workspace import WorkspaceContext, now


class CodingRuntime:
    """A complete coding-agent session state."""

    def __init__(
        self,
        session_id: str,
        workspace_root: Path | str,
        model: Any,
        storage_root: Path | str,
        model_factory: Callable[[], Any] | None = None,
        approval_policy: str = "auto",
    ) -> None:
        self.session_id = session_id
        self.workspace = WorkspaceContext(root=Path(workspace_root))
        self.model = model
        self.model_factory = model_factory or (lambda: model)
        self.storage_root = Path(storage_root)
        self.session_store = CodingSessionStore(self.storage_root / "sessions")
        self.run_store = RunStore(self.storage_root / "runs")
        self.session_event_bus = SessionEventBus(
            session_id=session_id,
            path=self.session_store.event_path(session_id),
        )
        self.session: dict[str, Any] = {
            "id": session_id,
            "workspace_root": str(self.workspace.root),
            "created_at": now(),
            "updated_at": now(),
            "history": [],
            "runtime_mode": {"mode": "default"},
            "todos": {"next_id": 1, "items": []},
        }
        self.todo_ledger = TodoLedger(self.session["todos"])
        self.plan_mode = PlanModeManager(self.workspace.root)
        self.worker_manager = WorkerManager(self.workspace, self.model_factory)
        self.approval_policy = approval_policy
        self.runtime_mode = "default"
        self.permission_checker = self._permission_checker()
        self.policy_checker = ToolPolicyChecker(self.workspace)
        self.tool_context = ToolContext(
            runtime=self,
            todo_ledger=self.todo_ledger,
            worker_manager=self.worker_manager,
        )
        self.tools = build_tool_registry(self.workspace, tool_context=self.tool_context)

    def enter_plan_mode(self, topic: str, path: str | None = None) -> str:
        """Switch to plan mode."""
        plan_path = self.plan_mode.enter(topic, path=path)
        self.runtime_mode = "plan"
        self.session["runtime_mode"] = self.plan_mode.to_dict()
        self.permission_checker = self._permission_checker()
        self._save_session()
        self.session_event_bus.emit("runtime_mode_changed", self.plan_mode.to_dict())
        return plan_path

    def exit_plan_mode(self) -> None:
        """Switch back to default mode."""
        self.plan_mode.exit()
        self.runtime_mode = "default"
        self.session["runtime_mode"] = self.plan_mode.to_dict()
        self.permission_checker = self._permission_checker()
        self._save_session()
        self.session_event_bus.emit("runtime_mode_changed", self.plan_mode.to_dict())

    async def run_turn(self, user_message: str) -> AsyncIterator[dict[str, Any]]:
        """Run one coding turn, persist events, and stream them to caller."""
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        self.run_store.start_run(run_id)
        self.session_event_bus.emit("turn_started", {"run_id": run_id})
        engine = Engine(
            model=self.model,
            workspace=self.workspace,
            tools=self.tools,
            context_manager=ContextManager(),
            permission_checker=self.permission_checker,
            policy_checker=self.policy_checker,
            history=self.session["history"],
            max_steps=50,
        )
        async for event in engine.run_turn(user_message):
            event = {"run_id": run_id, **event}
            self.run_store.append_trace(run_id, event)
            self.session_event_bus.emit(event["type"], event)
            self._sync_session_state()
            yield event
        self.session_event_bus.emit("turn_finished", {"run_id": run_id})
        self._save_session()

    def _permission_checker(self) -> PermissionChecker:
        return PermissionChecker(
            approval_policy="auto" if self.approval_policy == "auto" else "never",
            plan_mode=self.runtime_mode == "plan",
        )

    def _sync_session_state(self) -> None:
        self.session["updated_at"] = now()
        self.session["todos"] = self.todo_ledger.to_dict()
        self.session["runtime_mode"] = self.plan_mode.to_dict()

    def _save_session(self) -> None:
        self._sync_session_state()
        self.session_store.save(self.session)
