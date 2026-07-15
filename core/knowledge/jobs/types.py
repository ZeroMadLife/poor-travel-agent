"""Domain types for durable Knowledge Workspace ingestion jobs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

TERMINAL_ITEM_STATUSES = frozenset({"completed", "skipped", "cancelled", "dead_letter"})
TERMINAL_JOB_STATUSES = frozenset({"completed", "completed_with_errors", "cancelled"})


@dataclass(frozen=True, slots=True)
class ScannedKnowledgeFile:
    relative_path: str
    source_revision: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class KnowledgeJob:
    job_id: str
    workspace_id: str
    source_root_id: str
    source_kind: str
    source_label: str
    relative_directory: str
    pipeline_version: str
    status: str
    cancel_requested: bool
    total_items: int
    processed_items: int
    succeeded_items: int
    skipped_items: int
    failed_items: int
    cancelled_items: int
    latest_sequence: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class KnowledgeJobItem:
    item_id: str
    job_id: str
    relative_path: str
    source_revision: str
    status: str
    attempts: int
    max_attempts: int
    proposal_id: str | None
    error: str | None
    next_attempt_at: datetime | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class KnowledgeJobEvent:
    event_id: str
    job_id: str
    item_id: str | None
    sequence: int
    kind: str
    status: str
    detail: dict[str, str | int | bool | None]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class QueueMessage:
    message_id: str
    item_id: str


@dataclass(frozen=True, slots=True)
class IdempotencyClaim:
    outcome: str
    proposal_id: str | None = None
