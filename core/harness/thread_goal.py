"""Revisioned Thread Goal lifecycle on the shared Chat Harness journal."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from core.coding.persistence.session_event_journal import (
    SessionEventJournal,
    SessionRunLeaseConflictError,
    SessionThreadGoalConflictError,
)

GoalEvaluationStatus = Literal["satisfied", "blocked", "continue"]
GoalBlocker = Literal[
    "missing_evidence",
    "needs_user_input",
    "run_failed",
    "external_wait",
    "goal_not_met_yet",
    "no_progress",
]

_REFERENCE_KEYS = frozenset(
    {
        "evidence_ref",
        "evidence_refs",
        "citation_id",
        "artifact_ref",
        "result_ref",
        "source_ref",
        "page_revision",
        "revision_ref",
    }
)


class ThreadGoalError(RuntimeError):
    """Base Thread Goal service error."""


class ThreadGoalNotFoundError(ThreadGoalError):
    """No primary Goal is configured for this Thread."""


class ThreadGoalBusyError(ThreadGoalError):
    """The Goal cannot mutate while its session owns an active run lease."""


@dataclass(frozen=True, slots=True)
class ThreadGoalContinue:
    goal_id: str
    goal_revision: int
    prompt: str


class ThreadGoalService:
    """Validate and persist a single session-level Goal without a second runtime."""

    def __init__(self, journal: SessionEventJournal) -> None:
        self.journal = journal

    def get(self) -> dict[str, Any] | None:
        return self.journal.current_thread_goal()

    def upsert(
        self,
        *,
        description: str,
        completion_criteria: Iterable[str],
        expected_revision: int,
    ) -> dict[str, Any]:
        self._require_idle()
        description_text = _bounded_text(description, field="description", maximum=2_000)
        criteria = _criteria(completion_criteria)
        current = self.get()
        actual_revision = self.journal.current_thread_goal_revision()
        if actual_revision != expected_revision:
            # Journal remains the final atomic CAS authority. This early branch
            # avoids generating a new identity for an already-stale create.
            raise SessionThreadGoalConflictError(actual_revision)
        now = datetime.now(UTC).isoformat()
        goal_id = (
            str(current.get("goal_id"))
            if current
            else "goal-" + hashlib.sha256(self.journal.session_id.encode("utf-8")).hexdigest()[:20]
        )
        evaluation = {
            "status": "continue",
            "blocker": "goal_not_met_yet",
            "evidence_refs": [],
            "next_action": "开始执行当前目标并收集可验证证据",
            "source_run_id": None,
            "evaluated_at": now,
        }
        goal: dict[str, Any] = {
            "goal_id": goal_id,
            "revision": expected_revision + 1,
            "description": description_text,
            "completion_criteria": criteria,
            "status": "active",
            "evaluation": evaluation,
            "created_at": str(current.get("created_at")) if current else now,
            "updated_at": now,
        }
        try:
            stored = self.journal.append_thread_goal(
                event_type="thread_goal_updated",
                expected_revision=expected_revision,
                goal=goal,
            )
        except SessionRunLeaseConflictError as exc:
            raise ThreadGoalBusyError("Thread Goal cannot change while a run is active") from exc
        return dict(stored.payload["goal"])

    def clear(self, *, expected_revision: int) -> None:
        self._require_idle()
        if self.get() is None:
            raise ThreadGoalNotFoundError("Thread Goal is not configured")
        try:
            self.journal.clear_thread_goal(expected_revision=expected_revision)
        except SessionRunLeaseConflictError as exc:
            raise ThreadGoalBusyError("Thread Goal cannot change while a run is active") from exc

    def evaluate(self, *, expected_revision: int) -> dict[str, Any]:
        self._require_idle()
        current = self._current_at(expected_revision)
        terminal = self.journal.latest_terminal_event()
        now = datetime.now(UTC).isoformat()
        if terminal is None:
            status: GoalEvaluationStatus = "continue"
            blocker: GoalBlocker = "goal_not_met_yet"
            next_action = "开始执行当前目标并收集可验证证据"
            source_run_id = None
            refs: list[str] = []
        elif terminal.status == "completed":
            status = "continue"
            blocker = "goal_not_met_yet"
            next_action = "继续目标并补齐完成标准所需的可验证证据"
            source_run_id = terminal.run_id
            refs = _evidence_refs(self.journal.events_for_run(terminal.run_id))
        else:
            status = "blocked"
            blocker = "run_failed"
            next_action = "上一轮运行失败；检查错误证据后重新执行目标"
            source_run_id = terminal.run_id
            refs = _evidence_refs(self.journal.events_for_run(terminal.run_id))
        evaluation = {
            "status": status,
            "blocker": blocker,
            "evidence_refs": refs,
            "next_action": next_action,
            "source_run_id": source_run_id,
            "evaluated_at": now,
        }
        goal = {
            **current,
            "revision": expected_revision + 1,
            "status": "blocked" if status == "blocked" else "active",
            "evaluation": evaluation,
            "updated_at": now,
        }
        try:
            stored = self.journal.append_thread_goal(
                event_type="thread_goal_evaluated",
                expected_revision=expected_revision,
                goal=goal,
            )
        except SessionRunLeaseConflictError as exc:
            raise ThreadGoalBusyError("Thread Goal cannot change while a run is active") from exc
        return dict(stored.payload["goal"])

    def prepare_continue(self, *, expected_revision: int) -> ThreadGoalContinue:
        self._require_idle()
        current = self._current_at(expected_revision)
        criteria = "\n".join(
            f"- {item}" for item in current.get("completion_criteria", []) if str(item).strip()
        )
        evaluation = current.get("evaluation")
        next_action = (
            str(evaluation.get("next_action", "")).strip()
            if isinstance(evaluation, Mapping)
            else ""
        )
        prompt = (
            "继续当前 Thread Goal。只推进当前目标，不创建新目标。\n\n"
            f"目标：{current['description']}\n"
            f"完成标准：\n{criteria or '- 尚未补充'}\n"
            f"下一步：{next_action or '继续收集可验证证据'}\n\n"
            "请基于已有 timeline 和证据继续；需要外部输入或能力不可用时明确阻塞原因。"
        )
        return ThreadGoalContinue(
            goal_id=str(current["goal_id"]),
            goal_revision=int(current["revision"]),
            prompt=prompt,
        )

    def _current_at(self, expected_revision: int) -> dict[str, Any]:
        current = self.get()
        if current is None:
            raise ThreadGoalNotFoundError("Thread Goal is not configured")
        actual = int(current.get("revision", 0))
        if actual != expected_revision:
            raise SessionThreadGoalConflictError(actual)
        return current

    def _require_idle(self) -> None:
        if self.journal.active_run_id() is not None:
            raise ThreadGoalBusyError("Thread Goal cannot change while a run is active")


def _bounded_text(value: object, *, field: str, maximum: int) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip()
    if not text:
        raise ValueError(f"{field} must not be empty")
    if len(text) > maximum:
        raise ValueError(f"{field} exceeds {maximum} characters")
    return text


def _criteria(values: Iterable[str]) -> list[str]:
    items = [_bounded_text(value, field="completion criterion", maximum=500) for value in values]
    if not 1 <= len(items) <= 8:
        raise ValueError("completion_criteria must contain between 1 and 8 items")
    return items


def _evidence_refs(events: Iterable[object]) -> list[str]:
    refs: list[str] = []

    def visit(value: object, key: str = "") -> None:
        if len(refs) >= 32:
            return
        if isinstance(value, Mapping):
            for child_key, child in value.items():
                visit(child, str(child_key))
            return
        if isinstance(value, list | tuple):
            for child in value:
                visit(child, key)
            return
        if key in _REFERENCE_KEYS and isinstance(value, str):
            candidate = value.strip()[:512]
            if candidate and candidate not in refs:
                refs.append(candidate)

    for event in events:
        visit(getattr(event, "payload", None))
    return refs


__all__ = [
    "GoalBlocker",
    "GoalEvaluationStatus",
    "ThreadGoalBusyError",
    "ThreadGoalContinue",
    "ThreadGoalError",
    "ThreadGoalNotFoundError",
    "ThreadGoalService",
]
