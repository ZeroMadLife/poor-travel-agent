"""Memory manager combining working and durable memory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.coding.memory.durable import DurableMemory, MemoryFact, workspace_id_from_path
from core.coding.memory.working import WorkingMemory
from core.coding.persistence.memory_store import (
    MemoryCandidate,
    MemoryEvent,
    MemoryProposal,
    MemoryStore,
)


class MemoryManager:
    """Combine working memory (per-run) and durable memory (workspace-scoped)."""

    def __init__(self, storage_root: Path, workspace_root: Path) -> None:
        ws_id = workspace_id_from_path(workspace_root)
        self.durable = DurableMemory(storage_root, ws_id)
        self.memory_store = MemoryStore(storage_root, ws_id)
        self.working: WorkingMemory | None = None
        self._pending_proposal: list[MemoryFact] | None = None
        self._proposal_id: str = ""

    def build_working_memory(
        self, session: dict[str, Any], runtime_mode: str, permission_mode: str
    ) -> WorkingMemory:
        """Build working memory for the current run."""
        self.working = WorkingMemory.from_session(session, runtime_mode, permission_mode)
        return self.working

    def remember(
        self, content: str, topic: str = "project-conventions", source_ref: str = ""
    ) -> MemoryFact:
        """Explicitly remember a fact."""
        return self.durable.remember(content, topic=topic, source_ref=source_ref)

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
        """Generate dream proposals from daily logs (proposal only, no mutation).

        Persists the generated proposals as the pending proposal so they can be
        approved or rejected via ``approve_dream`` / ``reject_dream``.
        """
        facts = self.durable.list_facts()
        proposals = self.durable.propose_dream(facts)
        if proposals:
            from core.coding.context import now

            self._proposal_id = f"dream_{now().replace(':', '').replace('-', '')}"
            self._pending_proposal = proposals
            self.create_proposal(
                [MemoryCandidate(f.content, f.topic, "dream_proposal", f.source_ref, f.created_at) for f in proposals],
                reflection_id=self._proposal_id,
                proposal_id=self._proposal_id,
            )
        return proposals

    def create_proposal(
        self, candidates: list[MemoryCandidate], *, run_id: str = "", reflection_id: str = "",
        session_id: str = "", proposal_id: str | None = None,
    ) -> MemoryProposal:
        """Persist a proposal; candidates do not become active facts."""
        return self.memory_store.create_proposal(
            candidates, run_id=run_id, reflection_id=reflection_id,
            session_id=session_id, proposal_id=proposal_id,
        )

    def get_proposal(self, proposal_id: str) -> MemoryProposal | None:
        return self.memory_store.get_proposal(proposal_id)

    def list_proposals(self, status: str | None = None) -> list[MemoryProposal]:
        return self.memory_store.list_proposals(status)

    def approve(self, proposal_id: str, expected_revision: int = 0) -> MemoryProposal:
        proposal = self.memory_store.approve(proposal_id, expected_revision)
        if proposal.status == "approved":
            facts = [MemoryFact(topic=c.topic, content=c.content, source=c.source,
                                source_ref=c.source_ref, created_at=c.created_at,
                                status="proposed") for c in proposal.candidates]
            self.durable.approve_dream(facts)
        return proposal

    def reject(self, proposal_id: str, expected_revision: int = 0) -> MemoryProposal:
        return self.memory_store.reject(proposal_id, expected_revision)

    def list_memory_events(self, proposal_id: str | None = None) -> list[MemoryEvent]:
        return self.memory_store.list_events(proposal_id)

    def approve_dream(self) -> bool:
        """Write the pending proposal to durable files and clear it.

        Returns ``False`` when there is no pending proposal to approve.
        """
        if not self._pending_proposal:
            return False
        if self._proposal_id:
            self.approve(self._proposal_id)
        else:
            self.durable.approve_dream(self._pending_proposal)
        self._pending_proposal = None
        self._proposal_id = ""
        return True

    def reject_dream(self) -> bool:
        """Discard the pending proposal without writing."""
        self._pending_proposal = None
        self._proposal_id = ""
        return True

    @property
    def pending_proposal(self) -> dict[str, object] | None:
        """Return a serializable view of the pending proposal, or ``None``."""
        if not self._pending_proposal:
            return None
        return {
            "proposal_id": self._proposal_id,
            "facts": [
                {
                    "topic": f.topic,
                    "content": f.content,
                    "source_ref": f.source_ref,
                }
                for f in self._pending_proposal
            ],
        }
