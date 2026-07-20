from __future__ import annotations

from pathlib import Path

import pytest

from core.coding.persistence.session_event_journal import SessionEventJournal
from core.harness.thread_goal import (
    ThreadGoalBusyError,
    ThreadGoalService,
)


def test_thread_goal_service_upserts_evaluates_and_prepares_continue(tmp_path: Path) -> None:
    journal = SessionEventJournal(tmp_path, "session-1")
    service = ThreadGoalService(journal)
    created = service.upsert(
        description="研究 LangGraph checkpoint 恢复",
        completion_criteria=("返回官方引用", "解释 thread 与 checkpoint 的区别"),
        expected_revision=0,
    )

    assert created["revision"] == 1
    assert created["status"] == "active"
    assert created["evaluation"]["status"] == "continue"
    assert created["evaluation"]["blocker"] == "goal_not_met_yet"

    journal.append_terminal_once(
        run_id="run-failed",
        status="error",
        payload={"event": "run_error"},
    )
    evaluated = service.evaluate(expected_revision=1)
    assert evaluated["revision"] == 2
    assert evaluated["status"] == "blocked"
    assert evaluated["evaluation"]["status"] == "blocked"
    assert evaluated["evaluation"]["blocker"] == "run_failed"
    assert evaluated["evaluation"]["source_run_id"] == "run-failed"

    prepared = service.prepare_continue(expected_revision=2)
    assert prepared.goal_revision == 2
    assert "LangGraph checkpoint" in prepared.prompt
    assert "上一轮运行失败" in prepared.prompt


def test_thread_goal_mutations_fail_when_run_wins_after_idle_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal = SessionEventJournal(tmp_path, "session-1")
    service = ThreadGoalService(journal)
    journal.begin_run("run-active", owner_id="owner", owner_pid=-1)
    monkeypatch.setattr(journal, "active_run_id", lambda: None)

    with pytest.raises(ThreadGoalBusyError):
        service.upsert(
            description="不能在运行中替换",
            completion_criteria=("明确终态",),
            expected_revision=0,
        )


def test_thread_goal_recreate_uses_clear_tombstone_revision(tmp_path: Path) -> None:
    service = ThreadGoalService(SessionEventJournal(tmp_path, "session-1"))
    created = service.upsert(
        description="first",
        completion_criteria=("first criterion",),
        expected_revision=0,
    )
    service.clear(expected_revision=created["revision"])

    recreated = service.upsert(
        description="second",
        completion_criteria=("second criterion",),
        expected_revision=2,
    )

    assert recreated["revision"] == 3
