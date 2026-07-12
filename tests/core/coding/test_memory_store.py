from pathlib import Path

import pytest

from core.coding.memory import MemoryManager
from core.coding.persistence.memory_store import MemoryCandidate, MemoryConflictError, MemoryStore


def test_proposal_restart_and_no_mutation_before_approval(tmp_path: Path) -> None:
    ws = tmp_path / "repo"
    ws.mkdir()
    manager = MemoryManager(tmp_path / "storage", ws)
    proposal = manager.create_proposal([MemoryCandidate("use ruff")], run_id="run-1", reflection_id="r-1")
    assert manager.memory_store.list_facts() == []
    reopened = MemoryManager(tmp_path / "storage", ws)
    assert reopened.get_proposal(proposal.proposal_id) == proposal
    approved = reopened.approve(proposal.proposal_id, expected_revision=0)
    assert approved.status == "approved"
    assert [f.content for f in reopened.memory_store.list_facts()] == ["use ruff"]


def test_workspace_isolation_and_duplicate_hash(tmp_path: Path) -> None:
    a = MemoryStore(tmp_path / "storage", "workspace-a")
    b = MemoryStore(tmp_path / "storage", "workspace-b")
    a.create_proposal([MemoryCandidate("same")], proposal_id="a")
    a.approve("a", 0)
    b.create_proposal([MemoryCandidate("same")], proposal_id="b")
    b.approve("b", 0)
    assert len(a.list_facts()) == len(b.list_facts()) == 1
    c = a.create_proposal([MemoryCandidate("same")], proposal_id="a2")
    a.approve(c.proposal_id, 0)
    assert len(a.list_facts()) == 1


def test_cas_idempotency_and_audit_events(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "storage", "workspace")
    store.create_proposal([MemoryCandidate("fact")], proposal_id="p")
    with pytest.raises(MemoryConflictError):
        store.approve("p", expected_revision=4)
    approved = store.approve("p", expected_revision=0)
    assert store.approve("p", expected_revision=1) == approved
    with pytest.raises(MemoryConflictError):
        store.reject("p", expected_revision=1)
    events = store.list_events("p")
    assert [e.event_type for e in events] == ["proposal_created", "proposal_approved"]
    assert events[0].candidate_count == 1


def test_manager_approval_replay_does_not_duplicate_markdown_projection(tmp_path: Path) -> None:
    workspace = tmp_path / "repo"
    workspace.mkdir()
    manager = MemoryManager(tmp_path / "storage", workspace)
    proposal = manager.create_proposal([MemoryCandidate("once")], proposal_id="once")
    manager.approve(proposal.proposal_id, 0)
    first = len(manager.durable.list_facts())
    manager.approve(proposal.proposal_id, 1)
    assert len(manager.durable.list_facts()) == first
