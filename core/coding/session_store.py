"""Local JSON session storage for coding runtime."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, cast


class CodingSessionStore:
    """Persist coding session state under .coding/sessions."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def path(self, session_id: str) -> Path:
        return self.root / f"{_safe_session_id(session_id)}.json"

    def event_path(self, session_id: str) -> Path:
        return self.root / f"{_safe_session_id(session_id)}.events.jsonl"

    def save(self, session: dict[str, Any]) -> Path:
        """Atomically save a session JSON file."""
        path = self.path(str(session["id"]))
        payload = json.dumps(session, indent=2, ensure_ascii=False, sort_keys=True)
        with self._lock:
            tmp_path = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
            tmp_path.write_text(payload, encoding="utf-8")
            os.replace(tmp_path, path)
        return path

    def load(self, session_id: str) -> dict[str, Any]:
        """Load one session by id."""
        data = json.loads(self.path(session_id).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("session file must contain a JSON object")
        return cast(dict[str, Any], data)


def _safe_session_id(session_id: str) -> str:
    value = session_id.strip()
    if not value or value in {".", ".."} or "/" in value or "\\" in value:
        raise ValueError("invalid session id")
    return value
