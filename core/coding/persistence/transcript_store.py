"""Canonical append-only transcript persistence."""

from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast


@dataclass(frozen=True)
class TranscriptItem:
    """One canonical transcript entry."""

    message_id: str
    role: str
    content: str
    run_id: str = ""
    turn_id: str = ""
    call_id: str = ""
    artifact_ref: str = ""
    created_at: str = ""


class TranscriptStore:
    """Append transcript entries once and preserve all existing lines."""

    def __init__(self, root: Path, session_id: str) -> None:
        _validate_scope_id(session_id, "session")
        self.path = root / "evidence" / session_id / "transcript.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._message_ids = {item.message_id for item in self.read_all()}

    def append(self, item: TranscriptItem) -> bool:
        """Append ``item`` unless its message id was already persisted."""
        with self._lock:
            if item.message_id in self._message_ids:
                return False
            line = json.dumps(asdict(item), ensure_ascii=False, sort_keys=True) + "\n"
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
            self._message_ids.add(item.message_id)
            return True

    def read_all(self) -> list[TranscriptItem]:
        """Read all non-empty transcript lines in append order."""
        with self._lock:
            if not self.path.is_file():
                return []
            items: list[TranscriptItem] = []
            with self.path.open(encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    payload = cast(dict[str, str], json.loads(line))
                    items.append(TranscriptItem(**payload))
            return items


def _validate_scope_id(value: str, label: str) -> None:
    if not value or value in {".", ".."} or "/" in value or "\\" in value:
        raise ValueError(f"invalid {label} id")
