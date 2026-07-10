"""Evidence-backed memory tests: durable storage, working memory, dream proposals."""

from __future__ import annotations

from pathlib import Path

from core.coding.memory import (
    DurableMemory,
    MemoryManager,
    WorkingMemory,
    workspace_id_from_path,
)


def test_durable_memory_isolated_by_workspace(tmp_path: Path) -> None:
    """Two workspaces keep separate durable memory trees."""
    storage = tmp_path / "storage"
    ws_a = tmp_path / "repo_a"
    ws_b = tmp_path / "repo_b"
    ws_a.mkdir()
    ws_b.mkdir()

    mem_a = DurableMemory(storage, workspace_id_from_path(ws_a))
    mem_b = DurableMemory(storage, workspace_id_from_path(ws_b))

    mem_a.remember("repo A uses ruff", topic="project-conventions")
    mem_b.remember("repo B uses black", topic="project-conventions")

    facts_a = {f.content for f in mem_a.list_facts("project-conventions")}
    facts_b = {f.content for f in mem_b.list_facts("project-conventions")}

    assert facts_a == {"repo A uses ruff"}
    assert facts_b == {"repo B uses black"}
    assert "repo B uses black" not in facts_a
    # Different workspace ids -> different memory roots.
    assert mem_a.root != mem_b.root


def test_explicit_remember_survives_new_session(tmp_path: Path) -> None:
    """A remembered fact persists when a fresh DurableMemory is opened later."""
    storage = tmp_path / "storage"
    workspace = tmp_path / "repo"
    workspace.mkdir()
    ws_id = workspace_id_from_path(workspace)

    DurableMemory(storage, ws_id).remember(
        "prefer patch_file over write_file", topic="project-conventions"
    )

    # Simulate a new session re-opening the same workspace memory.
    reopened = DurableMemory(storage, ws_id)
    facts = [f.content for f in reopened.list_facts()]

    assert "prefer patch_file over write_file" in facts
    # The index reflects the persisted fact too.
    assert "prefer patch_file over write_file" in reopened.get_index()


def test_context_injection_respects_budget(tmp_path: Path) -> None:
    """select_for_context clips the index to the requested budget."""
    storage = tmp_path / "storage"
    workspace = tmp_path / "repo"
    workspace.mkdir()
    mem = DurableMemory(storage, workspace_id_from_path(workspace))

    # Store many facts so the index grows beyond a small budget.
    for index in range(50):
        mem.remember(f"convention number {index} with padding text", topic="decisions")

    block = mem.select_for_context(budget=300)
    assert len(block) <= 300 + len("\n...[truncated]")
    assert block.endswith("...[truncated]")
    # A generous budget returns the whole index untruncated.
    full = mem.select_for_context(budget=100000)
    assert full == mem.get_index()


def test_working_memory_from_session(tmp_path: Path) -> None:
    """WorkingMemory.from_session extracts task summary, recent files, and error."""
    session = {
        "history": [
            {"role": "user", "content": "earlier question"},
            {"role": "assistant", "content": "earlier answer"},
            {
                "role": "tool",
                "name": "read_file",
                "args": {"path": "src/app.py"},
                "content": "contents",
                "is_error": False,
            },
            {
                "role": "tool",
                "name": "patch_file",
                "args": {"path": "src/app.py", "old_text": "a", "new_text": "b"},
                "content": "patched",
                "is_error": False,
            },
            {
                "role": "tool",
                "name": "run_shell",
                "args": {"command": "make test"},
                "content": "boom: failure",
                "is_error": True,
            },
            {"role": "user", "content": "fix the failing test now"},
        ]
    }

    wm = WorkingMemory.from_session(session, runtime_mode="plan", permission_mode="auto")

    # The most recent user message becomes the task summary.
    assert wm.task_summary == "fix the failing test now"
    # The failing tool result is captured as the last error.
    assert "boom: failure" in wm.last_error
    # Recent files are deduplicated, most-recent-first; path taken from args.
    assert wm.recent_files[0]["path"] == "src/app.py"
    assert sum(1 for f in wm.recent_files if f["path"] == "src/app.py") == 1
    # Runtime/permission state is reflected.
    assert wm.plan_mode is True
    assert wm.permission_mode == "auto"
    # The context block renders without raising.
    block = wm.to_context_block()
    assert "<working-memory>" in block
    assert "fix the failing test now" in block
    assert "Plan mode: active" in block


def test_dream_proposal_does_not_mutate(tmp_path: Path) -> None:
    """propose_dream returns proposals without writing to durable files."""
    storage = tmp_path / "storage"
    workspace = tmp_path / "repo"
    workspace.mkdir()
    mem = DurableMemory(storage, workspace_id_from_path(workspace))

    mem.remember("use ruff for linting", topic="project-conventions")
    topic_path = mem.root / "project-conventions.md"
    before = topic_path.read_text(encoding="utf-8")

    proposals = mem.propose_dream(mem.list_facts())

    # All proposals are marked proposed, none active-written by the proposal step.
    assert proposals
    assert all(p.status == "proposed" for p in proposals)
    assert all(p.source == "dream_proposal" for p in proposals)
    # The durable topic file is unchanged by proposing.
    assert topic_path.read_text(encoding="utf-8") == before
    # No new active facts appear from proposing alone.
    assert len(mem.list_facts()) == 1


def test_memory_manager_combines_working_and_durable(tmp_path: Path) -> None:
    """MemoryManager assembles a context block from working + durable memory."""
    storage = tmp_path / "storage"
    workspace = tmp_path / "repo"
    workspace.mkdir()

    manager = MemoryManager(storage, workspace)
    manager.remember("always run ruff", topic="project-conventions")
    manager.build_working_memory(
        {"history": [{"role": "user", "content": "do the thing"}]},
        runtime_mode="default",
        permission_mode="default",
    )

    block = manager.get_context_block()

    assert "<working-memory>" in block
    assert "do the thing" in block
    assert "<durable-memory>" in block
    assert "always run ruff" in block
