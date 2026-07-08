"""Run trace store tests."""

from pathlib import Path

from core.coding.run_store import RunStore


def test_run_store_lists_run_summaries_from_trace(tmp_path: Path) -> None:
    """RunStore summarizes trace files for UI run history."""
    store = RunStore(tmp_path)
    store.start_run("run_a")
    store.append_trace("run_a", {"type": "model_requested", "created_at": "2026-07-08T10:00:00"})
    store.append_trace("run_a", {"type": "tool_call", "tool": "read_file"})
    store.append_trace("run_a", {"type": "tool_result", "tool": "read_file", "is_error": False})
    store.append_trace("run_a", {"type": "final", "content": "done"})

    summaries = store.list_runs()

    assert summaries == [
        {
            "run_id": "run_a",
            "status": "completed",
            "event_count": 4,
            "tool_count": 1,
            "error_count": 0,
            "last_event_type": "final",
            "started_at": "2026-07-08T10:00:00",
            "updated_at": "2026-07-08T10:00:00",
        }
    ]


def test_run_store_reads_trace_events(tmp_path: Path) -> None:
    """RunStore can return the full trace for a run."""
    store = RunStore(tmp_path)
    store.start_run("run_a")
    store.append_trace("run_a", {"type": "cancelled", "content": "stopped"})

    detail = store.get_run("run_a")

    assert detail["run_id"] == "run_a"
    assert detail["events"] == [{"type": "cancelled", "content": "stopped"}]
