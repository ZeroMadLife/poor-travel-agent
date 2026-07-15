from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from core.knowledge import (
    KnowledgeConflictError,
    KnowledgeSourceRoot,
    KnowledgeStore,
)


def _store(tmp_path: Path) -> tuple[KnowledgeStore, Path, Path]:
    vault = tmp_path / "vault"
    vault.mkdir()
    repository = tmp_path / "knowledge"
    repository.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    store = KnowledgeStore(
        repository,
        tmp_path / "state" / "knowledge.sqlite3",
        {
            "sage-learning": KnowledgeSourceRoot(
                root_id="sage-learning",
                kind="obsidian",
                label="Sage Learning",
                path=vault,
            )
        },
    )
    store.initialize()
    return store, vault, repository


def test_ingest_is_content_addressed_idempotent_and_does_not_write_wiki(
    tmp_path: Path,
) -> None:
    store, vault, repository = _store(tmp_path)
    note = vault / "harness.md"
    note.write_text("# Agent Harness\n\n可恢复执行。\n", encoding="utf-8")

    first = store.ingest("sage-learning", "harness.md")
    repeated = store.ingest("sage-learning", "harness.md")

    assert repeated == first
    assert first.status == "pending"
    assert first.revision == 0
    assert first.source_kind == "obsidian"
    assert first.source_revision.startswith("sha256:")
    assert first.raw_path.startswith("raw/sources/obsidian/")
    assert (repository / first.raw_path).read_text(encoding="utf-8") == note.read_text(
        encoding="utf-8"
    )
    assert not (repository / first.target_path).exists()
    assert store.summary().source_count == 1
    assert store.summary().pending_proposal_count == 1


def test_ingest_rejects_traversal_and_symlink_sources(tmp_path: Path) -> None:
    store, vault, _ = _store(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("# Secret\n", encoding="utf-8")
    (vault / "linked.md").symlink_to(outside)

    with pytest.raises(ValueError, match="relative source path"):
        store.ingest("sage-learning", "../outside.md")
    with pytest.raises(ValueError, match="symbolic link"):
        store.ingest("sage-learning", "linked.md")
    with pytest.raises(KeyError):
        store.ingest("unknown", "harness.md")

    (vault / "credential.md").write_text(
        "# Credential\n\nOPENAI_API_KEY=sk-1234567890abcdefghijklmnop\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="secret material"):
        store.ingest("sage-learning", "credential.md")


def test_approve_updates_git_wiki_and_reject_is_terminal(tmp_path: Path) -> None:
    store, vault, repository = _store(tmp_path)
    (vault / "harness.md").write_text("# Agent Harness\n\n第一版。\n", encoding="utf-8")
    proposal = store.ingest("sage-learning", "harness.md")

    approved = store.approve(proposal.proposal_id, expected_revision=0)

    assert approved.status == "approved"
    assert approved.projection_status == "complete"
    assert approved.revision == 1
    assert "第一版" in (repository / proposal.target_path).read_text(encoding="utf-8")
    assert proposal.target_path in (repository / "index.md").read_text(encoding="utf-8")
    assert proposal.proposal_id in (repository / "log.md").read_text(encoding="utf-8")
    assert len(store.list_pages()) == 1
    assert len(store.list_pages()[0].revisions) == 1
    commits = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    assert int(commits.stdout.strip()) == 2

    (vault / "rejected.md").write_text("# Rejected\n", encoding="utf-8")
    rejected_proposal = store.ingest("sage-learning", "rejected.md")
    rejected = store.reject(rejected_proposal.proposal_id, expected_revision=0)
    assert rejected.status == "rejected"
    with pytest.raises(KnowledgeConflictError):
        store.approve(rejected.proposal_id, expected_revision=1)


def test_stale_proposal_conflicts_and_rollback_creates_new_revision(
    tmp_path: Path,
) -> None:
    store, vault, repository = _store(tmp_path)
    note = vault / "harness.md"
    note.write_text("# Agent Harness\n\n第一版。\n", encoding="utf-8")
    store.approve(store.ingest("sage-learning", "harness.md").proposal_id, 0)
    page = store.list_pages()[0]
    first_revision = page.revisions[0]

    note.write_text("# Agent Harness\n\n第二版。\n", encoding="utf-8")
    second_proposal = store.ingest("sage-learning", "harness.md")
    second = store.approve(second_proposal.proposal_id, 0)
    assert second.status == "approved"
    current = store.list_pages()[0]
    assert len(current.revisions) == 2
    assert "第二版" in (repository / current.path).read_text(encoding="utf-8")

    rollback = store.propose_rollback(
        current.page_id,
        target_revision_id=first_revision.revision_id,
        expected_page_revision=current.current_revision,
    )
    assert rollback.status == "pending"
    assert "第二版" in (repository / current.path).read_text(encoding="utf-8")
    store.approve(rollback.proposal_id, expected_revision=0)

    restored = store.list_pages()[0]
    assert len(restored.revisions) == 3
    assert "第一版" in (repository / restored.path).read_text(encoding="utf-8")
    assert restored.revisions[-1].change_kind == "rollback"

    note.write_text("# Agent Harness\n\n第三版。\n", encoding="utf-8")
    stale = store.ingest("sage-learning", "harness.md")
    (repository / restored.path).write_text("manual edit\n", encoding="utf-8")
    with pytest.raises(KnowledgeConflictError, match="changed outside Sage"):
        store.approve(stale.proposal_id, expected_revision=0)
