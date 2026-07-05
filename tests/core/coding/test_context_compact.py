"""Coding context budget and compaction tests."""

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
