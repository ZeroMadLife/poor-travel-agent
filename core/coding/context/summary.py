"""Typed artifacts produced by structured context compaction."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

_HANDOFF_WARNING = "Historical handoff only; the latest user message always wins."


class CompactionSummary(BaseModel):
    """Validated semantic handoff for history removed from the active projection."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    goal: str
    user_constraints: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    completed_work: list[str] = Field(default_factory=list)
    active_todos: list[str] = Field(default_factory=list)
    files_read: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    tests: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    source_transcript_range: tuple[int, int]
    source_run_ids: list[str] = Field(default_factory=list)

    def render_for_prompt(self) -> str:
        """Render a deterministic prompt block with an instruction-precedence warning."""
        body = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return f"{_HANDOFF_WARNING}\n{body}"


@dataclass(frozen=True)
class CompactionCheckpoint:
    compaction_id: str
    transcript_start: int
    transcript_end: int
    summary: CompactionSummary
    summary_hash: str


@dataclass(frozen=True)
class CompactionResult:
    applied: bool
    projected_history: list[dict[str, Any]]
    checkpoint: CompactionCheckpoint | None
    before_tokens: int
    after_tokens: int
    archived_items: int
    reason: str = ""
