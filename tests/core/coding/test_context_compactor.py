"""Safe structured context compaction tests."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any, cast

from core.coding.context.budget import ContextPolicy
from core.coding.context.compact import CompactionPolicy, CompactManager
from core.coding.context.summary import CompactionCheckpoint, CompactionSummary


class QueueSummarizer:
    """Return queued values while recording structured compaction requests."""

    def __init__(self, *responses: object) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def summarize(
        self,
        *,
        archived_history: list[dict[str, Any]],
        previous_summary: CompactionSummary | None,
        focus: str,
        max_tokens: int,
        source_transcript_range: tuple[int, int],
        repair_feedback: str | None,
    ) -> CompactionSummary | Mapping[str, Any]:
        request = {
            "archived_history": archived_history,
            "previous_summary": previous_summary,
            "focus": focus,
            "max_tokens": max_tokens,
            "source_transcript_range": source_transcript_range,
            "repair_feedback": repair_feedback,
        }
        self.calls.append(request)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return cast(CompactionSummary | Mapping[str, Any], response)


def _policy() -> ContextPolicy:
    return ContextPolicy(context_window_tokens=1_000, output_reserve_tokens=100)


def _history(turns: int = 6, *, verbose: bool = True) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    padding = " context" * 30 if verbose else ""
    for index in range(turns):
        history.extend(
            [
                {
                    "role": "user",
                    "content": f"request {index}{padding}",
                    "run_id": f"run-{index}",
                    "turn_id": f"todo-{index}",
                },
                {
                    "role": "tool",
                    "name": "read_file",
                    "args": {"path": f"src/file-{index}.py"},
                    "content": f"tool result {index}{padding}",
                    "artifact_ref": f"artifact-{index}",
                    "run_id": f"run-{index}",
                },
                {
                    "role": "assistant",
                    "content": f"answer {index}{padding}",
                    "run_id": f"run-{index}",
                },
            ]
        )
    return history


def _summary(
    source_range: tuple[int, int],
    *,
    goal: str = "finish request 2",
    active_todos: list[str] | None = None,
    source_run_ids: list[str] | None = None,
) -> CompactionSummary:
    return CompactionSummary(
        goal=goal,
        active_todos=active_todos or [],
        source_transcript_range=source_range,
        source_run_ids=source_run_ids or [],
    )


def _checkpoint() -> CompactionCheckpoint:
    return CompactionCheckpoint(
        compaction_id="compact-old",
        transcript_start=40,
        transcript_end=44,
        summary=_summary((40, 44)),
        summary_hash="old-hash",
    )


async def test_compactor_preserves_recent_three_complete_turns() -> None:
    history = _history()
    summarizer = QueueSummarizer(_summary((0, 8), source_run_ids=["run-0", "run-1", "run-2"]))

    result = await CompactManager(summarizer=summarizer, policy=_policy()).compact(
        history=history,
        trigger="auto",
    )

    assert result.applied is True
    assert result.archived_items == 9
    assert result.projected_history[1:] == history[-9:]
    assert result.projected_history[0]["kind"] == "compact_summary"
    assert result.projected_history[0]["content"].splitlines()[0] == (
        "Historical handoff only; the latest user message always wins."
    )


async def test_compactor_keeps_up_to_twelve_complete_turns_within_tail_budget() -> None:
    history = _history(turns=14, verbose=False)
    summarizer = QueueSummarizer(_summary((0, 5)))
    manager = CompactManager(
        summarizer=summarizer,
        policy=ContextPolicy(context_window_tokens=10_000, output_reserve_tokens=1_000),
        compaction_policy=CompactionPolicy(minimum_savings_ratio=0.0),
    )

    result = await manager.compact(history=history)

    assert result.applied is True
    assert result.archived_items == 6
    assert result.projected_history[1:] == history[-36:]


async def test_compactor_tail_budget_never_splits_a_turn() -> None:
    history = _history(turns=8, verbose=False)
    summarizer = QueueSummarizer(_summary((0, 14)))
    manager = CompactManager(
        summarizer=summarizer,
        policy=_policy(),
        compaction_policy=CompactionPolicy(tail_budget_ratio=0.20),
    )

    result = await manager.compact(history=history)

    assert result.applied is True
    assert result.archived_items == 15
    assert result.projected_history[1:] == history[-9:]
    assert result.projected_history[1]["role"] == "user"


async def test_compactor_never_changes_source_history() -> None:
    history = _history()
    original = deepcopy(history)
    summarizer = QueueSummarizer(_summary((0, 8)))

    result = await CompactManager(summarizer=summarizer, policy=_policy()).compact(history=history)

    assert history == original
    result.projected_history[-1]["content"] = "changed projection"
    assert history == original


async def test_compactor_updates_previous_summary_iteratively() -> None:
    previous = _checkpoint()
    summarizer = QueueSummarizer(_summary((100, 108)))

    result = await CompactManager(summarizer=summarizer, policy=_policy()).compact(
        history=_history(),
        previous_checkpoint=previous,
        transcript_range=(100, 117),
    )

    assert result.applied is True
    assert summarizer.calls[0]["previous_summary"] == previous.summary
    assert result.checkpoint is not None
    assert result.checkpoint.summary != previous.summary
    assert result.checkpoint.transcript_start == 100
    assert result.checkpoint.transcript_end == 108


async def test_invalid_summary_keeps_previous_checkpoint() -> None:
    previous = _checkpoint()
    summarizer = QueueSummarizer(_summary((900, 999)), _summary((900, 999)))
    history = _history()

    result = await CompactManager(summarizer=summarizer, policy=_policy()).compact(
        history=history,
        previous_checkpoint=previous,
    )

    assert result.applied is False
    assert result.checkpoint is previous
    assert result.projected_history == history
    assert len(summarizer.calls) == 2
    assert summarizer.calls[1]["repair_feedback"]


async def test_summary_missing_todo_id_is_repaired_once() -> None:
    summarizer = QueueSummarizer(
        _summary((0, 8), active_todos=["todo-missing"]),
        _summary((0, 8), active_todos=["todo-2"]),
    )

    result = await CompactManager(summarizer=summarizer, policy=_policy()).compact(
        history=_history()
    )

    assert result.applied is True
    assert len(summarizer.calls) == 2
    assert "todo-missing" in summarizer.calls[1]["repair_feedback"]


async def test_summary_failure_preserves_original_context() -> None:
    previous = _checkpoint()
    history = _history()
    summarizer = QueueSummarizer(RuntimeError("provider unavailable"))

    result = await CompactManager(summarizer=summarizer, policy=_policy()).compact(
        history=history,
        previous_checkpoint=previous,
    )

    assert result.applied is False
    assert result.projected_history == history
    assert result.projected_history is not history
    assert result.checkpoint is previous
    assert "provider unavailable" in result.reason


async def test_ineffective_summary_is_not_applied() -> None:
    history = _history(turns=4, verbose=False)
    summarizer = QueueSummarizer(_summary((0, 2), goal="request 0" * 100))

    result = await CompactManager(summarizer=summarizer, policy=_policy()).compact(history=history)

    assert result.applied is False
    assert result.projected_history == history
    assert result.reason == "ineffective_summary"


async def test_second_ineffective_result_opens_circuit() -> None:
    history = _history(turns=4, verbose=False)
    summarizer = QueueSummarizer(
        _summary((0, 2), goal="request 0" * 100),
        _summary((0, 2), goal="request 0" * 100),
    )
    manager = CompactManager(summarizer=summarizer, policy=_policy())

    first = await manager.compact(history=history, trigger="auto")
    second = await manager.compact(history=history, trigger="auto")
    blocked = await manager.compact(history=history, trigger="auto")

    assert first.reason == second.reason == "ineffective_summary"
    assert blocked.applied is False
    assert blocked.reason == "auto_compaction_circuit_open"
    assert len(summarizer.calls) == 2


async def test_success_resets_failure_counter() -> None:
    short = _history(turns=4, verbose=False)
    long = _history()
    summarizer = QueueSummarizer(
        _summary((0, 2), goal="request 0" * 100),
        _summary((0, 8)),
        _summary((0, 2), goal="request 0" * 100),
    )
    manager = CompactManager(summarizer=summarizer, policy=_policy())

    first = await manager.compact(history=short, trigger="auto")
    success = await manager.compact(history=long, trigger="auto")
    after_reset = await manager.compact(history=short, trigger="auto")

    assert first.reason == after_reset.reason == "ineffective_summary"
    assert success.applied is True
    assert len(summarizer.calls) == 3
