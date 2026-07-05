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
