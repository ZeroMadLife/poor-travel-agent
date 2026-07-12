"""Durable, append-state compaction attempt artifacts."""

from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import os
import re
import secrets
import stat
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any

from core.coding.context.summary import CompactionCheckpoint, CompactionResult
from core.coding.context.workspace import now

_SAFE_ID = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
_FILE_FLAGS = os.O_CLOEXEC | os.O_NOFOLLOW


class CompactionStoreError(RuntimeError):
    """Base error for durable compaction state."""


class CompactionConflictError(CompactionStoreError):
    """An attempt id was reused with different content or state."""


class CompactionStore:
    """Persist one monotonic JSON state machine per compaction attempt."""

    def __init__(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if root.is_symlink():
            raise ValueError("trusted root must not be a symlink")
        self._root = root.resolve(strict=True)
        if not self._root.is_dir():
            raise ValueError("trusted root must be a directory")

    def begin(
        self,
        session_id: str,
        compaction_id: str,
        metadata: Mapping[str, Any],
    ) -> dict[str, Any]:
        _validate_id(session_id, "session")
        _validate_id(compaction_id, "compaction")
        normalized = _json_object(metadata, "metadata")
        with self._locked_directory(session_id, compaction_id) as directory_fd:
            existing = self._read_optional(directory_fd, compaction_id)
            if existing is not None:
                if existing.get("metadata") == normalized:
                    return existing
                raise CompactionConflictError("compaction attempt metadata conflict")
            timestamp = now()
            artifact = {
                "schema_version": 1,
                "session_id": session_id,
                "compaction_id": compaction_id,
                "status": "started",
                "metadata": normalized,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            self._publish(directory_fd, compaction_id, artifact)
            return artifact

    def complete(
        self,
        session_id: str,
        compaction_id: str,
        result: CompactionResult,
        *,
        checkpoint: CompactionCheckpoint | None = None,
        evidence: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        selected = checkpoint if checkpoint is not None else result.checkpoint
        if selected is None:
            raise ValueError("completed compaction requires a checkpoint")
        if not result.applied:
            raise ValueError("completed compaction result must be applied")
        if result.compaction_id != compaction_id or selected.compaction_id != compaction_id:
            raise ValueError("compaction_id does not match attempt")
        if result.checkpoint is not None and result.checkpoint != selected:
            raise ValueError("result checkpoint does not match selected checkpoint")
        terminal = {
            "result": _serialize_result(result),
            "checkpoint": _serialize_checkpoint(selected),
            "evidence": _json_object(evidence or {}, "evidence"),
        }
        return self._transition(session_id, compaction_id, "completed", terminal)

    def fail(
        self,
        session_id: str,
        compaction_id: str,
        result: CompactionResult,
    ) -> dict[str, Any]:
        if result.applied:
            raise ValueError("failed compaction result must not be applied")
        if result.compaction_id != compaction_id:
            raise ValueError("compaction_id does not match attempt")
        return self._transition(
            session_id,
            compaction_id,
            "failed",
            {"result": _serialize_result(result)},
        )

    def load(self, session_id: str, compaction_id: str) -> dict[str, Any] | None:
        _validate_id(session_id, "session")
        _validate_id(compaction_id, "compaction")
        with self._locked_directory(session_id, compaction_id) as directory_fd:
            return self._read_optional(directory_fd, compaction_id)

    def load_latest(self, session_id: str) -> dict[str, Any] | None:
        _validate_id(session_id, "session")
        directory_fd = _open_components(self._root, ("evidence", session_id, "compactions"))
        try:
            candidates: list[dict[str, Any]] = []
            for name in os.listdir(directory_fd):
                if not name.endswith(".json"):
                    continue
                compaction_id = name[:-5]
                if not _SAFE_ID.fullmatch(compaction_id):
                    continue
                artifact = self._read_optional(directory_fd, compaction_id)
                if artifact is not None:
                    candidates.append(artifact)
            if not candidates:
                return None
            return max(
                candidates,
                key=lambda item: (str(item.get("updated_at", "")), str(item["compaction_id"])),
            )
        finally:
            os.close(directory_fd)

    def verify_checkpoint(
        self,
        session_id: str,
        checkpoint: CompactionCheckpoint,
    ) -> bool:
        try:
            artifact = self.load(session_id, checkpoint.compaction_id)
            if artifact is None or artifact.get("status") != "completed":
                return False
            if (
                artifact.get("schema_version") != 1
                or artifact.get("session_id") != session_id
                or artifact.get("compaction_id") != checkpoint.compaction_id
            ):
                return False
            stored = artifact.get("checkpoint")
            expected = _serialize_checkpoint(checkpoint)
            if stored != expected:
                return False
            expected_summary_hash = hashlib.sha256(
                (
                    f"{checkpoint.previous_summary_hash}\n"
                    f"{checkpoint.evidence_hash}\n"
                    f"{checkpoint.summary.render_for_prompt()}"
                ).encode()
            ).hexdigest()
            if not checkpoint.evidence_hash or checkpoint.summary_hash != expected_summary_hash:
                return False
            result = artifact.get("result")
            return (
                isinstance(result, dict)
                and result.get("applied") is True
                and result.get("compaction_id") == checkpoint.compaction_id
                and result.get("checkpoint") == expected
                and checkpoint.summary.source_transcript_range
                == (checkpoint.transcript_start, checkpoint.transcript_end)
            )
        except (OSError, ValueError, CompactionStoreError, json.JSONDecodeError):
            return False

    def _transition(
        self,
        session_id: str,
        compaction_id: str,
        status: str,
        terminal: dict[str, Any],
    ) -> dict[str, Any]:
        _validate_id(session_id, "session")
        _validate_id(compaction_id, "compaction")
        with self._locked_directory(session_id, compaction_id) as directory_fd:
            existing = self._read_optional(directory_fd, compaction_id)
            if existing is None:
                raise CompactionConflictError("compaction attempt was not started")
            current = existing.get("status")
            if current == status:
                if all(existing.get(key) == value for key, value in terminal.items()):
                    return existing
                raise CompactionConflictError("terminal compaction payload conflict")
            if current != "started":
                raise CompactionConflictError(f"cannot transition {current!r} to {status!r}")
            artifact = {
                **existing,
                "status": status,
                **terminal,
                "updated_at": now(),
            }
            self._publish(directory_fd, compaction_id, artifact)
            return artifact

    @contextmanager
    def _locked_directory(self, session_id: str, compaction_id: str) -> Iterator[int]:
        directory_fd = _open_components(self._root, ("evidence", session_id, "compactions"))
        lock_name = f".{compaction_id}.lock"
        lock_fd = -1
        try:
            lock_fd = _open_or_create_regular(directory_fd, lock_name)
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            yield directory_fd
        finally:
            if lock_fd >= 0:
                with suppress(OSError):
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
            os.close(directory_fd)

    @staticmethod
    def _read_optional(directory_fd: int, compaction_id: str) -> dict[str, Any] | None:
        name = f"{compaction_id}.json"
        try:
            file_fd = _open_regular(directory_fd, name, os.O_RDONLY)
        except FileNotFoundError:
            return None
        try:
            chunks: list[bytes] = []
            while chunk := os.read(file_fd, 64 * 1024):
                chunks.append(chunk)
            value = json.loads(b"".join(chunks).decode("utf-8"))
            if not isinstance(value, dict):
                raise CompactionStoreError("compaction artifact must be a JSON object")
            return value
        finally:
            os.close(file_fd)

    @staticmethod
    def _publish(directory_fd: int, compaction_id: str, artifact: dict[str, Any]) -> None:
        target = f"{compaction_id}.json"
        _reject_unsafe_target(directory_fd, target)
        payload = json.dumps(
            artifact,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        temp_name = ""
        temp_fd = -1
        try:
            for _ in range(100):
                temp_name = f".{compaction_id}.{secrets.token_hex(16)}.tmp"
                try:
                    temp_fd = os.open(
                        temp_name,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | _FILE_FLAGS,
                        0o600,
                        dir_fd=directory_fd,
                    )
                    break
                except FileExistsError:
                    continue
            if temp_fd < 0:
                raise OSError("unable to allocate compaction temporary file")
            os.fchmod(temp_fd, 0o600)
            _write_all(temp_fd, payload)
            os.fsync(temp_fd)
            os.close(temp_fd)
            temp_fd = -1
            os.replace(temp_name, target, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
            temp_name = ""
            os.fsync(directory_fd)
        finally:
            if temp_fd >= 0:
                os.close(temp_fd)
            if temp_name:
                with suppress(FileNotFoundError):
                    os.unlink(temp_name, dir_fd=directory_fd)


def _open_components(root: Path, components: tuple[str, ...]) -> int:
    directory_fd = os.open(root, _DIRECTORY_FLAGS)
    try:
        os.fchmod(directory_fd, 0o700)
        for component in components:
            try:
                os.mkdir(component, 0o700, dir_fd=directory_fd)
                os.fsync(directory_fd)
            except FileExistsError:
                pass
            try:
                next_fd = os.open(component, _DIRECTORY_FLAGS, dir_fd=directory_fd)
            except OSError as exc:
                if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
                    raise ValueError(f"symlink path component rejected: {component}") from exc
                raise
            os.fchmod(next_fd, 0o700)
            os.close(directory_fd)
            directory_fd = next_fd
        return directory_fd
    except BaseException:
        os.close(directory_fd)
        raise


def _open_or_create_regular(directory_fd: int, name: str) -> int:
    try:
        file_fd = os.open(
            name,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | _FILE_FLAGS,
            0o600,
            dir_fd=directory_fd,
        )
        os.fsync(file_fd)
        os.fsync(directory_fd)
    except FileExistsError:
        return _open_regular(directory_fd, name, os.O_RDWR)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise ValueError(f"symlink file rejected: {name}") from exc
        raise
    _validate_regular(file_fd, name)
    return file_fd


def _open_regular(directory_fd: int, name: str, flags: int) -> int:
    try:
        file_fd = os.open(name, flags | _FILE_FLAGS, dir_fd=directory_fd)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise ValueError(f"symlink file rejected: {name}") from exc
        raise
    try:
        _validate_regular(file_fd, name)
    except BaseException:
        os.close(file_fd)
        raise
    return file_fd


def _validate_regular(file_fd: int, name: str) -> None:
    metadata = os.fstat(file_fd)
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"non-regular file rejected: {name}")
    if metadata.st_nlink != 1:
        raise ValueError(f"hardlink file rejected: {name}")


def _reject_unsafe_target(directory_fd: int, name: str) -> None:
    try:
        metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if stat.S_ISLNK(metadata.st_mode):
        raise ValueError(f"symlink file rejected: {name}")
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"non-regular file rejected: {name}")
    if metadata.st_nlink != 1:
        raise ValueError(f"hardlink file rejected: {name}")


def _write_all(file_fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(file_fd, view)
        if written == 0:
            raise OSError("short write")
        view = view[written:]


def _validate_id(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value) or value in {".", ".."}:
        raise ValueError(f"invalid {label} id")


def _json_object(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        decoded = json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be JSON-safe") from exc
    if not isinstance(decoded, dict):
        raise TypeError(f"{label} must be a JSON object")
    return decoded


def _serialize_checkpoint(checkpoint: CompactionCheckpoint) -> dict[str, Any]:
    return {
        "compaction_id": checkpoint.compaction_id,
        "transcript_start": checkpoint.transcript_start,
        "transcript_end": checkpoint.transcript_end,
        "summary": checkpoint.summary.model_dump(mode="json"),
        "summary_hash": checkpoint.summary_hash,
        "previous_summary_hash": checkpoint.previous_summary_hash,
        "evidence_hash": checkpoint.evidence_hash,
        "prefix_hash": checkpoint.prefix_hash,
    }


def _serialize_result(result: CompactionResult) -> dict[str, Any]:
    return {
        "applied": result.applied,
        "checkpoint": (
            _serialize_checkpoint(result.checkpoint) if result.checkpoint is not None else None
        ),
        "before_tokens": result.before_tokens,
        "after_tokens": result.after_tokens,
        "archived_items": result.archived_items,
        "reason": result.reason,
        "compaction_id": result.compaction_id,
        "trigger": result.trigger,
        "retryable": result.retryable,
        "cooldown_until": result.cooldown_until,
    }
