"""Memory manager combining working and durable memory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.coding.memory.durable import DurableMemory, MemoryFact, workspace_id_from_path
from core.coding.memory.working import WorkingMemory


class MemoryManager:
    """Combine working memory (per-run) and durable memory (workspace-scoped)."""

    def __init__(self, storage_root: Path, workspace_root: Path) -> None:
        ws_id = workspace_id_from_path(workspace_root)
        self.durable = DurableMemory(storage_root, ws_id)
        self.working: WorkingMemory | None = None

    def build_working_memory(
        self, session: dict[str, Any], runtime_mode: str, permission_mode: str
    ) -> WorkingMemory:
        """Build working memory for the current run."""
        self.working = WorkingMemory.from_session(session, runtime_mode, permission_mode)
        return self.working

    def remember(self, content: str, topic: str = "project-conventions") -> MemoryFact:
        """Explicitly remember a fact."""
        return self.durable.remember(content, topic=topic)

    def get_context_block(self) -> str:
        """Return combined memory context for prompt injection."""
        parts: list[str] = []
        if self.working:
            parts.append(self.working.to_context_block())
        durable = self.durable.select_for_context(budget=2000)
        if durable:
            parts.append(f"<durable-memory>\n{durable}\n</durable-memory>")
        return "\n\n".join(parts)

    def get_index(self) -> str:
        return self.durable.get_index()

    def list_facts(self, topic: str = "") -> list[MemoryFact]:
        return self.durable.list_facts(topic)

    def propose_dream(self) -> list[MemoryFact]:
        """Generate dream proposals from daily logs (proposal only, no mutation)."""
        # Simple: return existing facts as proposals for user review
        facts = self.durable.list_facts()
        return self.durable.propose_dream(facts)

    def approve_dream(self, facts: list[MemoryFact]) -> None:
        self.durable.approve_dream(facts)
