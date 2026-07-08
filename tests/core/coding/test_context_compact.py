"""Coding context budget and compaction tests."""

from datetime import date

from core.coding.compact import CompactManager
from core.coding.context_manager import ContextManager


def test_context_manager_keeps_prompt_under_budget() -> None:
    """ContextManager reduces old history to keep the prompt within budget."""
    history = [
        {"role": "user", "content": "old question " + ("x" * 80)},
        {"role": "assistant", "content": "old answer " + ("y" * 80)},
    ] * 30
    manager = ContextManager(total_budget=600)

    prompt, metadata = manager.build(
        user_message="current request must remain visible",
        history=history,
        tools=["read_file: read a file", "search: search files"],
    )

    assert len(prompt) <= 600
    assert "current request must remain visible" in prompt
    assert metadata["prompt_over_budget"] is False
    assert (
        metadata["sections"]["history"]["rendered_chars"]
        < metadata["sections"]["history"]["raw_chars"]
    )


def test_compact_manager_summarizes_old_turns_and_keeps_recent_turns() -> None:
    """CompactManager folds old turns into a compact_summary item."""
    history = [
        {"role": "user", "content": f"request {index}"}
        if offset == 0
        else {"role": "assistant", "content": f"answer {index}"}
        for index in range(5)
        for offset in range(2)
    ]

    new_history, summary = CompactManager().compact(history, keep_recent_turns=2)

    assert new_history[0]["role"] == "system"
    assert new_history[0]["kind"] == "compact_summary"
    assert "request 2" in new_history[0]["content"]
    assert [item["content"] for item in new_history[-4:]] == [
        "request 3",
        "answer 3",
        "request 4",
        "answer 4",
    ]
    assert summary["pre_items"] == 10
    assert summary["post_items"] == 5


def test_context_manager_reuses_cached_system_prompt_across_turns() -> None:
    """Stable system prompt is built once for repeated builds with the same tools."""
    manager = ContextManager(today=lambda: date(2026, 7, 8))
    tools = ["read_file: read a file", "search: search files"]

    first, first_metadata = manager.build("first request", tools=tools)
    second, second_metadata = manager.build("second request", tools=tools)

    assert manager.system_prompt_build_count == 1
    assert "Session date: 2026-07-08" in first
    assert "Session date: 2026-07-08" in second
    assert first_metadata["sections"]["prefix"] == second_metadata["sections"]["prefix"]


def test_context_manager_invalidate_rebuilds_cached_system_prompt() -> None:
    """Explicit invalidation forces the next build to rebuild the system prompt."""
    current_day = date(2026, 7, 8)
    manager = ContextManager(today=lambda: current_day)

    first = manager.build_system_prompt_once(["read_file: read a file"])
    manager.invalidate_system_prompt()
    second = manager.build_system_prompt_once(["read_file: read a file"])

    assert first == second
    assert manager.system_prompt_build_count == 2


def test_context_manager_uses_date_precision_for_volatile_tier() -> None:
    """Volatile prompt uses date precision, not second/minute precision."""
    manager = ContextManager(today=lambda: date(2026, 7, 8))

    prompt = manager.build_system_prompt_once([])

    assert "Session date: 2026-07-08" in prompt
    assert "T" not in prompt
    assert ":00" not in prompt


def test_compact_manager_invalidates_context_cache_after_compaction() -> None:
    """Compaction can invalidate the prompt cache when memory/history changed."""
    manager = ContextManager()
    manager.build_system_prompt_once(["read_file: read a file"])
    assert manager.system_prompt_build_count == 1

    history = [
        {"role": "user", "content": f"request {index}"}
        if offset == 0
        else {"role": "assistant", "content": f"answer {index}"}
        for index in range(4)
        for offset in range(2)
    ]

    CompactManager().compact(history, keep_recent_turns=1, context_manager=manager)
    manager.build_system_prompt_once(["read_file: read a file"])

    assert manager.system_prompt_build_count == 2
