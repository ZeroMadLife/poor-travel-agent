"""WorkspaceDiffTracker tests: bounded diff artifact for coding runs."""

from pathlib import Path

from core.coding.context.workspace_diff import (
    MAX_DIFF_FILES,
    WorkspaceDiffTracker,
)


def test_clean_run_empty_diff(tmp_path: Path) -> None:
    """No file changes between snapshots -> empty diff."""
    (tmp_path / "README.md").write_text("# Sage\n", encoding="utf-8")
    tracker = WorkspaceDiffTracker(tmp_path)
    tracker.snapshot_before_run()
    diff = tracker.snapshot_after_run("run_clean")

    assert diff.run_id == "run_clean"
    assert diff.changed_files == []
    assert diff.file_count == 0
    assert diff.truncated is False


def test_write_file_produces_diff(tmp_path: Path) -> None:
    """Writing a new file after the before snapshot shows up as 'added'."""
    (tmp_path / "README.md").write_text("# Sage\n", encoding="utf-8")
    tracker = WorkspaceDiffTracker(tmp_path)
    tracker.snapshot_before_run()

    (tmp_path / "note.txt").write_text("hello world\n", encoding="utf-8")
    diff = tracker.snapshot_after_run("run_add")

    assert diff.file_count == 1
    change = diff.changed_files[0]
    assert change.path == "note.txt"
    assert change.status == "added"
    assert change.binary is False
    assert change.after_hash
    assert change.before_hash == ""
    # The added diff should reference the new file.
    assert "note.txt" in change.diff
    assert "+hello world" in change.diff


def test_modify_file_produces_unified_diff(tmp_path: Path) -> None:
    """Modifying a text file produces a real unified diff patch."""
    (tmp_path / "src.py").write_text("line one\nline two\n", encoding="utf-8")
    tracker = WorkspaceDiffTracker(tmp_path)
    tracker.snapshot_before_run()

    (tmp_path / "src.py").write_text("line one\nline two edited\nline three\n", encoding="utf-8")
    diff = tracker.snapshot_after_run("run_modify")

    assert diff.file_count == 1
    change = diff.changed_files[0]
    assert change.path == "src.py"
    assert change.status == "modified"
    assert change.binary is False
    assert change.before_hash
    assert change.after_hash
    assert change.before_hash != change.after_hash
    # Unified diff markers are present.
    assert "--- a/src.py" in change.diff
    assert "+++ b/src.py" in change.diff
    assert "-line two" in change.diff
    assert "+line two edited" in change.diff
    assert "+line three" in change.diff


def test_delete_file_in_diff(tmp_path: Path) -> None:
    """Deleting a file after the before snapshot shows up as 'deleted'."""
    (tmp_path / "keep.txt").write_text("keep\n", encoding="utf-8")
    (tmp_path / "drop.txt").write_text("drop\n", encoding="utf-8")
    tracker = WorkspaceDiffTracker(tmp_path)
    tracker.snapshot_before_run()

    (tmp_path / "drop.txt").unlink()
    diff = tracker.snapshot_after_run("run_delete")

    statuses = {change.path: change.status for change in diff.changed_files}
    assert statuses["drop.txt"] == "deleted"
    deleted = next(c for c in diff.changed_files if c.path == "drop.txt")
    assert deleted.before_hash
    assert deleted.after_hash == ""


def test_ignored_secrets_not_in_diff(tmp_path: Path) -> None:
    """.env files and .git/.coding dirs never appear in the diff."""
    (tmp_path / "README.md").write_text("# Sage\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=token\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    (tmp_path / ".coding").mkdir()
    (tmp_path / ".coding" / "state.json").write_text("{}", encoding="utf-8")
    tracker = WorkspaceDiffTracker(tmp_path)
    tracker.snapshot_before_run()

    # Mutate the .env (a secret) and a .git file after the snapshot; neither
    # should ever be tracked, so they must not appear in the diff.
    (tmp_path / ".env").write_text("SECRET=leaked\n", encoding="utf-8")
    (tmp_path / ".git" / "config").write_text("[new]\n", encoding="utf-8")
    diff = tracker.snapshot_after_run("run_secrets")

    paths = {change.path for change in diff.changed_files}
    assert ".env" not in paths
    assert ".git/config" not in paths
    assert ".coding/state.json" not in paths


def test_binary_file_marked_binary(tmp_path: Path) -> None:
    """A file with null bytes is marked binary and has no diff content."""
    (tmp_path / "README.md").write_text("# Sage\n", encoding="utf-8")
    tracker = WorkspaceDiffTracker(tmp_path)
    tracker.snapshot_before_run()

    # Write a file whose leading bytes contain a null byte -> detected as binary.
    (tmp_path / "blob.bin").write_bytes(b"\x00\x01\x02\x03binary")
    diff = tracker.snapshot_after_run("run_binary")

    change = next(c for c in diff.changed_files if c.path == "blob.bin")
    assert change.status == "added"
    assert change.binary is True
    # Binary files must not carry a unified diff body.
    assert change.diff == ""


def test_large_diff_truncated(tmp_path: Path) -> None:
    """More than MAX_DIFF_FILES changed files -> truncated=True and capped list."""
    (tmp_path / "README.md").write_text("# Sage\n", encoding="utf-8")
    tracker = WorkspaceDiffTracker(tmp_path)
    tracker.snapshot_before_run()

    # Create more changed files than the cap.
    for i in range(MAX_DIFF_FILES + 5):
        (tmp_path / f"f{i:03d}.txt").write_text(f"content {i}\n", encoding="utf-8")
    diff = tracker.snapshot_after_run("run_truncated")

    assert diff.truncated is True
    assert len(diff.changed_files) == MAX_DIFF_FILES
    assert diff.file_count == MAX_DIFF_FILES
