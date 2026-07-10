"""Workspace-scoped durable memory with file-backed storage."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import ClassVar

from core.coding.context import now


@dataclass
class MemoryFact:
    """One durable memory fact with provenance."""

    topic: str = "project-conventions"  # "project-conventions" or "decisions"
    content: str = ""
    source: str = "explicit_remember"  # "explicit_remember", "plan_approved", "run_success"
    source_ref: str = ""  # run_id or plan_path
    created_at: str = ""
    reviewed_at: str = ""
    status: str = "active"  # "active", "proposed", "rejected"


class DurableMemory:
    """File-backed durable memory scoped to one workspace."""

    TOPIC_FILES: ClassVar[dict[str, str]] = {
        "project-conventions": "project-conventions.md",
        "decisions": "decisions.md",
    }

    def __init__(self, storage_root: Path, workspace_id: str) -> None:
        self.root = storage_root / "memory" / workspace_id
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "daily").mkdir(exist_ok=True)

    @property
    def index_path(self) -> Path:
        return self.root / "MEMORY.md"

    def remember(
        self,
        content: str,
        topic: str = "project-conventions",
        source: str = "explicit_remember",
        source_ref: str = "",
    ) -> MemoryFact:
        """Append an explicit memory fact to the daily log and topic file."""
        fact = MemoryFact(
            topic=topic,
            content=content.strip(),
            source=source,
            source_ref=source_ref,
            created_at=now(),
            status="active",
        )
        self._append_daily_log(fact)
        self._append_topic_file(fact)
        self._rebuild_index()
        return fact

    def list_facts(self, topic: str = "") -> list[MemoryFact]:
        """Return facts from topic files. If topic='', return all."""
        facts: list[MemoryFact] = []
        topics = [topic] if topic else list(self.TOPIC_FILES.keys())
        for t in topics:
            path = self.root / self.TOPIC_FILES.get(t, "")
            if not path.is_file():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("- "):
                    facts.append(
                        MemoryFact(topic=t, content=line[2:].strip(), status="active")
                    )
        return facts

    def get_index(self) -> str:
        """Return the MEMORY.md index content."""
        if self.index_path.is_file():
            return self.index_path.read_text(encoding="utf-8")
        return ""

    def select_for_context(self, budget: int = 2000) -> str:
        """Return a budgeted string of durable memory for context injection."""
        index = self.get_index()
        if not index:
            return ""
        if len(index) <= budget:
            return index
        return index[:budget] + "\n...[truncated]"

    def propose_dream(self, facts: list[MemoryFact]) -> list[MemoryFact]:
        """Create proposals (does not mutate durable files).

        Returns facts with status='proposed'.
        """
        return [
            MemoryFact(
                topic=f.topic,
                content=f.content,
                source="dream_proposal",
                source_ref=f.source_ref,
                created_at=f.created_at,
                status="proposed",
            )
            for f in facts
        ]

    def approve_dream(self, facts: list[MemoryFact]) -> None:
        """Write approved dream facts to durable files."""
        for fact in facts:
            if fact.status == "proposed":
                fact.status = "active"
                self._append_topic_file(fact)
        self._rebuild_index()

    def _append_daily_log(self, fact: MemoryFact) -> None:
        daily_path = self.root / "daily" / f"{date.today().isoformat()}.md"
        entry = f"- [{fact.created_at}] ({fact.topic}) {fact.content}"
        if fact.source_ref:
            entry += f" [ref: {fact.source_ref}]"
        entry += f" [source: {fact.source}]\n"
        with daily_path.open("a", encoding="utf-8") as f:
            f.write(entry)

    def _append_topic_file(self, fact: MemoryFact) -> None:
        topic_path = self.root / self.TOPIC_FILES.get(fact.topic, "decisions.md")
        with topic_path.open("a", encoding="utf-8") as f:
            f.write(f"- {fact.content}\n")

    def _rebuild_index(self) -> None:
        lines = ["# Memory Index", ""]
        for topic, filename in self.TOPIC_FILES.items():
            path = self.root / filename
            if not path.is_file():
                continue
            topic_lines = path.read_text(encoding="utf-8").splitlines()
            count = sum(1 for line in topic_lines if line.strip().startswith("- "))
            lines.append(f"## {topic} ({count} facts)")
            for line in topic_lines:
                if line.strip().startswith("- "):
                    lines.append(f"  {line.strip()}")
            lines.append("")
        self.index_path.write_text("\n".join(lines), encoding="utf-8")


def workspace_id_from_path(workspace_root: Path) -> str:
    """Derive a stable workspace identifier from the canonical path."""
    return hashlib.sha256(str(workspace_root.resolve()).encode()).hexdigest()[:16]
