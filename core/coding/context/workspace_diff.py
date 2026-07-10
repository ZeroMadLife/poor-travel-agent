"""Bounded workspace diff tracking for coding runs."""

from __future__ import annotations

import difflib
import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Patterns to ignore (never diff these)
IGNORED_DIRS = {
    ".git",
    ".coding",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
}
IGNORED_FILE_PATTERNS = (".env", ".DS_Store", ".pyc", ".so", ".dylib", ".lock")
MAX_FILE_SIZE = 256 * 1024  # 256KB - files larger than this are marked "truncated"
MAX_DIFF_FILES = 50  # Maximum number of changed files to track
# Small text files (<= this many bytes) have their before-content stored so a
# real unified diff can be generated after the run.
STORE_CONTENT_LIMIT = 16 * 1024  # 16KB


@dataclass
class FileSnapshot:
    """Content hash + metadata for one file."""

    path: str
    hash: str = ""
    size: int = 0
    is_text: bool = True
    exists: bool = True
    content: str = ""


@dataclass
class FileChange:
    """One changed file between before/after snapshots."""

    path: str
    status: str  # "added", "modified", "deleted"
    before_hash: str = ""
    after_hash: str = ""
    diff: str = ""
    truncated: bool = False
    binary: bool = False
    ignored_sensitive: bool = False


@dataclass
class WorkspaceDiff:
    """Bounded diff artifact for one run."""

    run_id: str
    changed_files: list[FileChange] = field(default_factory=list)
    file_count: int = 0
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "changed_files": [
                {
                    "path": f.path,
                    "status": f.status,
                    "before_hash": f.before_hash,
                    "after_hash": f.after_hash,
                    "diff": f.diff,
                    "truncated": f.truncated,
                    "binary": f.binary,
                    "ignored_sensitive": f.ignored_sensitive,
                }
                for f in self.changed_files
            ],
            "file_count": self.file_count,
            "truncated": self.truncated,
        }


class WorkspaceDiffTracker:
    """Track workspace file changes across a run lifecycle."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self._before: dict[str, FileSnapshot] = {}

    def snapshot_before_run(self) -> None:
        """Capture workspace state before the run starts."""
        self._before = self._scan_workspace()

    def snapshot_after_run(self, run_id: str) -> WorkspaceDiff:
        """Compare current state with before snapshot, return diff artifact."""
        after = self._scan_workspace()
        changes: list[FileChange] = []

        all_paths = set(self._before.keys()) | set(after.keys())
        for path in sorted(all_paths):
            before = self._before.get(path)
            after_snap = after.get(path)

            if before and after_snap and before.hash == after_snap.hash:
                continue  # unchanged

            if before and not after_snap:
                # deleted
                changes.append(
                    FileChange(
                        path=path,
                        status="deleted",
                        before_hash=before.hash,
                        after_hash="",
                    )
                )
            elif not before and after_snap:
                # added
                change = FileChange(
                    path=path,
                    status="added",
                    before_hash="",
                    after_hash=after_snap.hash,
                )
                if not after_snap.is_text:
                    change.binary = True
                else:
                    change.diff = self._generate_added_diff(path, after_snap)
                changes.append(change)
            elif before and after_snap and before.hash != after_snap.hash:
                # modified
                change = FileChange(
                    path=path,
                    status="modified",
                    before_hash=before.hash,
                    after_hash=after_snap.hash,
                )
                if not before.is_text or not after_snap.is_text:
                    change.binary = True
                else:
                    change.diff = self._generate_diff(path, before, after_snap)
                changes.append(change)

            if len(changes) >= MAX_DIFF_FILES:
                break

        truncated = len(all_paths) > MAX_DIFF_FILES
        return WorkspaceDiff(
            run_id=run_id,
            changed_files=changes,
            file_count=len(changes),
            truncated=truncated,
        )

    def write_artifact(self, diff: WorkspaceDiff, evidence_root: Path) -> Path:
        """Write diff artifact to evidence directory."""
        diff_dir = evidence_root / diff.run_id
        diff_dir.mkdir(parents=True, exist_ok=True)
        diff_path = diff_dir / "diff.json"
        diff_path.write_text(
            json.dumps(diff.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return diff_path

    def _scan_workspace(self) -> dict[str, FileSnapshot]:
        """Scan workspace and return path -> snapshot mapping."""
        snapshots: dict[str, FileSnapshot] = {}
        for root, dirs, files in os.walk(self.workspace_root):
            # Filter ignored dirs in-place
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for fname in files:
                if any(
                    fname.endswith(pat) or fname.startswith(pat)
                    for pat in IGNORED_FILE_PATTERNS
                ):
                    continue
                fpath = Path(root) / fname
                rel_path = str(fpath.relative_to(self.workspace_root))
                try:
                    stat = fpath.stat()
                except OSError:
                    continue
                snap = FileSnapshot(path=rel_path, size=stat.st_size)
                if stat.st_size > MAX_FILE_SIZE:
                    snap.is_text = False
                else:
                    try:
                        content_bytes = fpath.read_bytes()
                        snap.hash = hashlib.sha256(content_bytes).hexdigest()
                        snap.is_text = self._is_text(content_bytes)
                        # Store content for small text files so a real unified
                        # diff can be generated after the run.
                        if snap.is_text and stat.st_size <= STORE_CONTENT_LIMIT:
                            snap.content = content_bytes.decode("utf-8", errors="replace")
                    except (OSError, PermissionError):
                        snap.exists = False
                snapshots[rel_path] = snap
        return snapshots

    @staticmethod
    def _is_text(content: bytes) -> bool:
        """Heuristic: check if content is text (no null bytes in first 8KB)."""
        return b"\x00" not in content[:8192]

    def _generate_diff(
        self, rel_path: str, before: FileSnapshot, after: FileSnapshot
    ) -> str:
        """Generate unified diff for a modified text file."""
        after_text = after.content
        if not after_text:
            # After content wasn't stored (too large); read it now if possible.
            fpath = self.workspace_root / rel_path
            try:
                after_text = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return ""
        before_lines = before.content.splitlines(keepends=True)
        after_lines = after_text.splitlines(keepends=True)
        diff = difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
        )
        return "".join(diff)[:MAX_FILE_SIZE]  # Truncate to prevent huge diffs

    def _generate_added_diff(self, rel_path: str, after: FileSnapshot) -> str:
        """Generate unified diff for a newly added text file."""
        after_text = after.content
        if not after_text:
            fpath = self.workspace_root / rel_path
            try:
                after_text = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return ""
        after_lines = after_text.splitlines(keepends=True)
        diff = difflib.unified_diff(
            [],
            after_lines,
            fromfile="/dev/null",
            tofile=f"b/{rel_path}",
        )
        return "".join(diff)[:MAX_FILE_SIZE]  # Truncate to prevent huge diffs
