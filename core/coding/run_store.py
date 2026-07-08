"""Per-run trace persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RunStore:
    """Persist trace files for individual coding runs."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def start_run(self, run_id: str) -> Path:
        """Create and return a run directory."""
        path = self.root / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def append_trace(self, run_id: str, event: dict[str, Any]) -> Path:
        """Append one trace event."""
        path = self.root / run_id / "trace.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return path

    def list_runs(self, limit: int = 30) -> list[dict[str, Any]]:
        """Return run summaries ordered by most recently updated."""
        summaries: list[dict[str, Any]] = []
        for path in self.root.iterdir():
            if not path.is_dir():
                continue
            summary = self._summarize_run(path.name)
            if summary is not None:
                summaries.append(summary)
        return sorted(summaries, key=lambda item: str(item["updated_at"]), reverse=True)[:limit]

    def get_run(self, run_id: str) -> dict[str, Any]:
        """Return one run trace."""
        events = self._read_events(run_id)
        if not events:
            raise FileNotFoundError(run_id)
        return {"run_id": run_id, "events": events}

    def _summarize_run(self, run_id: str) -> dict[str, Any] | None:
        events = self._read_events(run_id)
        if not events:
            return None
        first = events[0]
        last = events[-1]
        return {
            "run_id": run_id,
            "status": _status_from_events(events),
            "event_count": len(events),
            "tool_count": sum(1 for event in events if event.get("type") == "tool_call"),
            "error_count": sum(
                1 for event in events if event.get("type") == "error" or event.get("is_error")
            ),
            "last_event_type": str(last.get("type", "")),
            "started_at": str(first.get("created_at") or first.get("timestamp") or ""),
            "updated_at": str(last.get("created_at") or first.get("created_at") or ""),
        }

    def _read_events(self, run_id: str) -> list[dict[str, Any]]:
        path = self.root / run_id / "trace.jsonl"
        if not path.is_file():
            return []
        events: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                events.append(event)
        return events


def _status_from_events(events: list[dict[str, Any]]) -> str:
    event_types = [str(event.get("type", "")) for event in events]
    if "cancelled" in event_types:
        return "cancelled"
    if "error" in event_types:
        return "error"
    if "final" in event_types:
        return "completed"
    if "step_limit" in event_types:
        return "step_limit"
    return "running"
