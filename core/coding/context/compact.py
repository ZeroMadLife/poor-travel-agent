"""Safe structured history compaction for coding sessions."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4

from core.coding.context.budget import ContextPolicy, TokenCounter
from core.coding.context.summary import (
    CompactionCheckpoint,
    CompactionResult,
    CompactionSummary,
)
from core.coding.context.workspace import now


class Summarizer(Protocol):
    async def summarize(
        self,
        *,
        archived_history: list[dict[str, Any]],
        previous_summary: CompactionSummary | None,
        focus: str,
        max_tokens: int,
        source_transcript_range: tuple[int, int],
        repair_feedback: str | None,
    ) -> CompactionSummary | Mapping[str, Any]: ...


class CacheInvalidator(Protocol):
    def invalidate_system_prompt(self) -> None: ...


@dataclass(frozen=True)
class CompactionPolicy:
    min_recent_turns: int = 3
    max_recent_turns: int = 12
    tail_budget_ratio: float = 0.20
    minimum_savings_ratio: float = 0.10
    ineffective_limit: int = 2

    def __post_init__(self) -> None:
        if self.min_recent_turns < 1:
            raise ValueError("min_recent_turns must be at least one")
        if self.max_recent_turns < self.min_recent_turns:
            raise ValueError("max_recent_turns must not be less than min_recent_turns")
        if not 0.0 < self.tail_budget_ratio <= 1.0:
            raise ValueError("tail_budget_ratio must be within (0, 1]")
        if not 0.0 <= self.minimum_savings_ratio <= 1.0:
            raise ValueError("minimum_savings_ratio must be within [0, 1]")
        if self.ineffective_limit < 1:
            raise ValueError("ineffective_limit must be at least one")


class CompactManager:
    def __init__(
        self,
        *,
        summarizer: Summarizer,
        policy: ContextPolicy,
        counter: TokenCounter | None = None,
        compaction_policy: CompactionPolicy | None = None,
    ) -> None:
        self.summarizer = summarizer
        self.policy = policy
        self.counter = counter or TokenCounter()
        self.compaction_policy = compaction_policy or CompactionPolicy()
        self._ineffective_results = 0
        self._auto_circuit_open = False

    async def compact(
        self,
        history: list[dict[str, Any]],
        *,
        trigger: str = "manual",
        focus: str = "",
        previous_checkpoint: CompactionCheckpoint | None = None,
        transcript_range: tuple[int, int] | None = None,
        context_manager: CacheInvalidator | None = None,
    ) -> CompactionResult:
        original = deepcopy(history)
        before_tokens = self._count_history(original)
        if trigger == "auto" and self._auto_circuit_open:
            return self._unchanged(
                original,
                previous_checkpoint,
                before_tokens,
                "auto_compaction_circuit_open",
            )

        archived, tail = self._split_history(original)
        if not archived:
            return self._unchanged(
                original, previous_checkpoint, before_tokens, "insufficient_history"
            )
        start = transcript_range[0] if transcript_range is not None else 0
        archived_range = (start, start + len(archived) - 1)
        max_tokens = max(
            1,
            min(int(self.policy.context_window_tokens * 0.05), 12_000),
        )
        archived_history = deepcopy(archived)
        previous_summary = previous_checkpoint.summary if previous_checkpoint is not None else None
        try:
            raw_summary = await self.summarizer.summarize(
                archived_history=archived_history,
                previous_summary=previous_summary,
                focus=focus,
                max_tokens=max_tokens,
                source_transcript_range=archived_range,
                repair_feedback=None,
            )
            summary = CompactionSummary.model_validate(raw_summary)
            feedback = self._validate_summary(summary, archived, archived_range)
        except Exception as exc:
            return self._unchanged(original, previous_checkpoint, before_tokens, str(exc))
        if feedback:
            try:
                repaired = await self.summarizer.summarize(
                    archived_history=archived_history,
                    previous_summary=previous_summary,
                    focus=focus,
                    max_tokens=max_tokens,
                    source_transcript_range=archived_range,
                    repair_feedback=feedback,
                )
                summary = CompactionSummary.model_validate(repaired)
                feedback = self._validate_summary(summary, archived, archived_range)
            except Exception as exc:
                return self._unchanged(original, previous_checkpoint, before_tokens, str(exc))
            if feedback:
                return self._unchanged(original, previous_checkpoint, before_tokens, feedback)

        summary_item = {
            "role": "system",
            "kind": "compact_summary",
            "content": summary.render_for_prompt(),
            "created_at": now(),
        }
        projected = [summary_item, *deepcopy(tail)]
        after_tokens = self._count_history(projected)
        savings_ratio = (before_tokens - after_tokens) / before_tokens
        if savings_ratio < self.compaction_policy.minimum_savings_ratio:
            self._ineffective_results += 1
            if self._ineffective_results >= self.compaction_policy.ineffective_limit:
                self._auto_circuit_open = True
            return CompactionResult(
                applied=False,
                projected_history=original,
                checkpoint=previous_checkpoint,
                before_tokens=before_tokens,
                after_tokens=after_tokens,
                archived_items=0,
                reason="ineffective_summary",
            )

        digest = hashlib.sha256(summary.render_for_prompt().encode("utf-8")).hexdigest()
        checkpoint = CompactionCheckpoint(
            compaction_id=f"compact-{uuid4().hex}",
            transcript_start=archived_range[0],
            transcript_end=archived_range[1],
            summary=summary,
            summary_hash=digest,
        )
        self._ineffective_results = 0
        self._auto_circuit_open = False
        if context_manager is not None:
            context_manager.invalidate_system_prompt()
        return CompactionResult(
            applied=True,
            projected_history=projected,
            checkpoint=checkpoint,
            before_tokens=before_tokens,
            after_tokens=after_tokens,
            archived_items=len(archived),
        )

    def _split_history(
        self, history: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        turns: list[list[dict[str, Any]]] = []
        prefix: list[dict[str, Any]] = []
        current: list[dict[str, Any]] | None = None
        for item in history:
            if item.get("role") == "user":
                if current is not None:
                    turns.append(current)
                current = [item]
            elif current is None:
                prefix.append(item)
            else:
                current.append(item)
        if current is not None:
            turns.append(current)
        keep = min(len(turns), self.compaction_policy.min_recent_turns)
        max_keep = min(len(turns), self.compaction_policy.max_recent_turns)
        tail_budget = int(
            self.policy.context_window_tokens * self.compaction_policy.tail_budget_ratio
        )
        while keep < max_keep:
            candidate = [item for turn in turns[-(keep + 1) :] for item in turn]
            if self._count_history(candidate) > tail_budget:
                break
            keep += 1
        archived_turns = turns[:-keep] if keep else turns
        tail_turns = turns[-keep:] if keep else []
        return (
            [*prefix, *(item for turn in archived_turns for item in turn)],
            [item for turn in tail_turns for item in turn],
        )

    def _count_history(self, history: list[dict[str, Any]]) -> int:
        rendered = json.dumps(history, ensure_ascii=False, sort_keys=True, default=str)
        return self.counter.count(rendered).tokens

    @staticmethod
    def _validate_summary(
        summary: CompactionSummary,
        archived: list[dict[str, Any]],
        archived_range: tuple[int, int],
    ) -> str:
        errors: list[str] = []
        if summary.source_transcript_range != archived_range:
            errors.append(
                f"source_transcript_range must be {archived_range}, "
                f"got {summary.source_transcript_range}"
            )

        evidence = json.dumps(archived, ensure_ascii=False, sort_keys=True, default=str)
        for field in (
            "active_todos",
            "files_read",
            "files_modified",
            "tests",
            "artifact_refs",
        ):
            for reference in getattr(summary, field):
                if reference not in evidence:
                    errors.append(f"{field} reference missing from evidence: {reference}")

        run_ids = {str(item["run_id"]) for item in archived if item.get("run_id") not in (None, "")}
        for run_id in summary.source_run_ids:
            if run_id not in run_ids:
                errors.append(f"source_run_ids reference missing from evidence: {run_id}")
        return "; ".join(errors)

    @staticmethod
    def _unchanged(
        history: list[dict[str, Any]],
        checkpoint: CompactionCheckpoint | None,
        tokens: int,
        reason: str,
    ) -> CompactionResult:
        return CompactionResult(False, history, checkpoint, tokens, tokens, 0, reason)
