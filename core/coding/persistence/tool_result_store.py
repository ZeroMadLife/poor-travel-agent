"""Durable full-result artifacts with bounded transcript previews."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

PERSIST_THRESHOLD_BYTES = 16 * 1024
PREVIEW_LINES = 200
PREVIEW_CHARS = 12_000

_HEAD_LINES = 120
_TAIL_LINES = PREVIEW_LINES - _HEAD_LINES


@dataclass(frozen=True)
class ArchivedToolResult:
    """A persisted tool result and its bounded preview."""

    artifact_ref: str
    artifact_path: Path
    preview: str
    original_chars: int
    truncated: bool


class ToolResultStore:
    """Persist complete tool output before deriving a bounded preview."""

    def __init__(self, root: Path, session_id: str, run_id: str) -> None:
        _validate_scope_id(session_id, "session")
        _validate_scope_id(run_id, "run")
        self.root = root / "evidence" / session_id / "runs" / run_id / "tool-results"

    def archive(self, call_id: str, content: str) -> ArchivedToolResult:
        """Atomically persist ``content``, then return its transcript preview."""
        _validate_scope_id(call_id, "call")
        self.root.mkdir(parents=True, exist_ok=True)
        artifact_ref = f"{call_id}.txt"
        artifact_path = self.root / artifact_ref
        self._replace_artifact(artifact_path, content)

        preview = _bounded_preview(content, call_id)
        return ArchivedToolResult(
            artifact_ref=artifact_ref,
            artifact_path=artifact_path,
            preview=preview,
            original_chars=len(content),
            truncated=preview != content,
        )

    def _replace_artifact(self, artifact_path: Path, content: str) -> None:
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.root,
                prefix=f".{artifact_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_path, 0o600)
            os.replace(temp_path, artifact_path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()


def _bounded_preview(content: str, call_id: str) -> str:
    lines = content.splitlines(keepends=True)
    selected = content
    if len(lines) > PREVIEW_LINES:
        selected = "".join(lines[:_HEAD_LINES] + lines[-_TAIL_LINES:])

    if selected == content and len(selected) <= PREVIEW_CHARS:
        return content

    marker = f"\n[full result: {call_id}]"
    budget = PREVIEW_CHARS - len(marker)
    if len(selected) > budget:
        head_chars = budget * _HEAD_LINES // PREVIEW_LINES
        tail_chars = budget - head_chars
        selected = selected[:head_chars] + selected[-tail_chars:]
    return selected + marker


def _validate_scope_id(value: str, label: str) -> None:
    if not value or value in {".", ".."} or "/" in value or "\\" in value:
        raise ValueError(f"invalid {label} id")
