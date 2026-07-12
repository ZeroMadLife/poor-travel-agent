"""Workspace-scoped SQLite storage for durable memory proposals and facts."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class MemoryStoreError(RuntimeError):
    """Base error for memory persistence."""


class MemoryConflictError(MemoryStoreError):
    """Raised when a proposal revision or fact conflicts."""


@dataclass(frozen=True)
class MemoryCandidate:
    content: str
    topic: str = "project-conventions"
    source: str = "dream_proposal"
    source_ref: str = ""
    created_at: str = ""

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content.strip().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MemoryProposal:
    proposal_id: str
    workspace_id: str
    candidates: tuple[MemoryCandidate, ...]
    status: str
    revision: int
    session_id: str = ""
    run_id: str = ""
    reflection_id: str = ""
    base_revision: int = 0
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class MemoryEvent:
    event_id: str
    event_type: str
    proposal_id: str
    workspace_id: str
    session_id: str = ""
    run_id: str = ""
    reflection_id: str = ""
    candidate_count: int = 0
    base_revision: int = 0
    revision: int = 0
    created_at: str = ""


class MemoryStore:
    """Small transactional SQLite store scoped to one workspace."""

    def __init__(self, storage_root: Path, workspace_id: str) -> None:
        if not workspace_id or any(c in workspace_id for c in "/\\"):
            raise ValueError("invalid workspace id")
        self.root = storage_root / "memory" / workspace_id
        self.root.mkdir(parents=True, exist_ok=True)
        with suppress(OSError):
            os.chmod(self.root, 0o700)
        self.path = self.root / "memory.sqlite3"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS memory_facts (
                    content_hash TEXT PRIMARY KEY, content TEXT NOT NULL,
                    topic TEXT NOT NULL, source TEXT NOT NULL, source_ref TEXT NOT NULL,
                    created_at TEXT NOT NULL, proposal_id TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS memory_proposals (
                    proposal_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL,
                    candidates_json TEXT NOT NULL, status TEXT NOT NULL,
                    revision INTEGER NOT NULL, session_id TEXT NOT NULL DEFAULT '',
                    run_id TEXT NOT NULL DEFAULT '', reflection_id TEXT NOT NULL DEFAULT '',
                    base_revision INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memory_events (
                    event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL,
                    proposal_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                    session_id TEXT NOT NULL DEFAULT '', run_id TEXT NOT NULL DEFAULT '',
                    reflection_id TEXT NOT NULL DEFAULT '', candidate_count INTEGER NOT NULL,
                    base_revision INTEGER NOT NULL, revision INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS memory_events_proposal_idx
                    ON memory_events(proposal_id, created_at);
                """
            )
            with suppress(OSError):
                os.chmod(self.path, 0o600)

    def create_proposal(
        self, candidates: Iterable[MemoryCandidate], *, session_id: str = "",
        run_id: str = "", reflection_id: str = "", proposal_id: str | None = None,
    ) -> MemoryProposal:
        values = tuple(c for c in candidates if c.content.strip())
        if not values:
            raise ValueError("proposal requires at least one candidate")
        # Deduplicate within a proposal while preserving order.
        unique: list[MemoryCandidate] = []
        seen: set[str] = set()
        for candidate in values:
            if candidate.content_hash not in seen:
                unique.append(candidate)
                seen.add(candidate.content_hash)
        now = _now()
        proposal = proposal_id or f"prop_{uuid.uuid4().hex}"
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            base = int(db.execute("SELECT COUNT(*) FROM memory_facts").fetchone()[0])
            payload = json.dumps([c.__dict__ for c in unique], ensure_ascii=False, sort_keys=True)
            db.execute("INSERT INTO memory_proposals VALUES (?, ?, ?, 'pending', 0, ?, ?, ?, ?, ?, ?)",
                       (proposal, self._workspace_id(), payload, session_id, run_id,
                        reflection_id, base, now, now))
            self._event(db, "proposal_created", proposal, self._workspace_id(), session_id, run_id, reflection_id,
                        len(unique), base, 0, now)
            db.commit()
        return self.get_proposal(proposal)  # type: ignore[return-value]

    def get_proposal(self, proposal_id: str) -> MemoryProposal | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM memory_proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
        return _proposal(row) if row else None

    def list_proposals(self, status: str | None = None) -> list[MemoryProposal]:
        with self._connect() as db:
            query = "SELECT * FROM memory_proposals"
            args: tuple[Any, ...] = ()
            if status:
                query += " WHERE status=?"
                args = (status,)
            query += " ORDER BY created_at"
            rows = db.execute(query, args).fetchall()
        return [_proposal(r) for r in rows]

    def approve(self, proposal_id: str, expected_revision: int) -> MemoryProposal:
        return self._transition(proposal_id, expected_revision, "approved")

    def reject(self, proposal_id: str, expected_revision: int) -> MemoryProposal:
        return self._transition(proposal_id, expected_revision, "rejected")

    def _transition(self, proposal_id: str, expected: int, status: str) -> MemoryProposal:
        now = _now()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM memory_proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
            if row is None:
                raise KeyError(proposal_id)
            current = _proposal(row)
            if current.revision != expected:
                raise MemoryConflictError(f"proposal revision conflict: expected {expected}, got {current.revision}")
            if current.status != "pending":
                if current.status == status:
                    db.commit()
                    return current
                raise MemoryConflictError(f"proposal already {current.status}")
            new_revision = current.revision + 1
            if status == "approved":
                for candidate in current.candidates:
                    db.execute("INSERT OR IGNORE INTO memory_facts VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (candidate.content_hash, candidate.content, candidate.topic,
                                candidate.source, candidate.source_ref, candidate.created_at or now, proposal_id))
            db.execute("UPDATE memory_proposals SET status=?, revision=?, updated_at=? WHERE proposal_id=?",
                       (status, new_revision, now, proposal_id))
            self._event(db, f"proposal_{status}", proposal_id, current.workspace_id, current.session_id, current.run_id,
                        current.reflection_id, len(current.candidates), current.base_revision,
                        new_revision, now)
            db.commit()
        return self.get_proposal(proposal_id)  # type: ignore[return-value]

    def list_facts(self) -> list[MemoryCandidate]:
        with self._connect() as db:
            rows = db.execute("SELECT content, topic, source, source_ref, created_at FROM memory_facts ORDER BY rowid").fetchall()
        return [MemoryCandidate(**dict(r)) for r in rows]

    def list_events(self, proposal_id: str | None = None) -> list[MemoryEvent]:
        with self._connect() as db:
            if proposal_id:
                rows = db.execute("SELECT * FROM memory_events WHERE proposal_id=? ORDER BY rowid", (proposal_id,)).fetchall()
            else:
                rows = db.execute("SELECT * FROM memory_events ORDER BY rowid").fetchall()
        return [MemoryEvent(**dict(r)) for r in rows]

    def _workspace_id(self) -> str:
        return self.root.name

    @staticmethod
    def _event(db: sqlite3.Connection, event_type: str, proposal_id: str, workspace_id: str, session_id: str,
               run_id: str, reflection_id: str, count: int, base: int, revision: int, now: str) -> None:
        db.execute("INSERT INTO memory_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (uuid.uuid4().hex, event_type, proposal_id, workspace_id, session_id, run_id, reflection_id, count, base, revision, now))


def _proposal(row: sqlite3.Row) -> MemoryProposal:
    data = dict(row)
    candidates = tuple(MemoryCandidate(**item) for item in json.loads(data.pop("candidates_json")))
    data["candidates"] = candidates
    return MemoryProposal(**data)


def _now() -> str:
    from core.coding.context.workspace import now
    return now()
