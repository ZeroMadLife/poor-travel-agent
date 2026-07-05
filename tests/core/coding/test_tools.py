"""Coding core tool tests."""

import os
import sys
from pathlib import Path

from core.coding.tools.registry import build_tool_registry
from core.coding.workspace import WorkspaceContext


def _workspace(tmp_path: Path) -> WorkspaceContext:
    return WorkspaceContext(root=tmp_path)


def test_list_files_marks_files_and_directories_and_ignores_noise(tmp_path: Path) -> None:
    """list_files returns stable file/directory markers and skips ignored names."""
    (tmp_path / "src").mkdir()
    (tmp_path / "README.md").write_text("TourSwarm", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    tools = build_tool_registry(_workspace(tmp_path))

    result = tools["list_files"].execute({"path": "."})

    assert result.is_error is False
    assert "[D] src" in result.content
    assert "[F] README.md" in result.content
    assert ".git" not in result.content


def test_read_file_returns_numbered_line_range(tmp_path: Path) -> None:
    """read_file reads a selected range with line numbers."""
    (tmp_path / "README.md").write_text("one\ntwo\nthree\n", encoding="utf-8")
    tools = build_tool_registry(_workspace(tmp_path))

    result = tools["read_file"].execute({"path": "README.md", "start": 2, "end": 3})

    assert result.is_error is False
    assert "# README.md" in result.content
    assert "   2: two" in result.content
    assert "   3: three" in result.content


def test_search_finds_matches_in_workspace(tmp_path: Path) -> None:
    """search finds text matches under the workspace."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def alpha():\n    return 1\n", encoding="utf-8")
    tools = build_tool_registry(_workspace(tmp_path))

    result = tools["search"].execute({"pattern": "alpha", "path": "."})

    assert result.is_error is False
    assert "src/app.py:1" in result.content


def test_patch_file_requires_unique_old_text(tmp_path: Path) -> None:
    """patch_file rejects ambiguous replacements and applies unique replacements."""
    target = tmp_path / "app.py"
    target.write_text("value = 1\nvalue = 1\n", encoding="utf-8")
    tools = build_tool_registry(_workspace(tmp_path))

    duplicate = tools["patch_file"].execute(
        {"path": "app.py", "old_text": "value = 1", "new_text": "value = 2"}
    )
    assert duplicate.is_error is True
    assert "exactly once" in duplicate.content

    target.write_text("value = 1\n", encoding="utf-8")
    unique = tools["patch_file"].execute(
        {"path": "app.py", "old_text": "value = 1", "new_text": "value = 2"}
    )
    assert unique.is_error is False
    assert target.read_text(encoding="utf-8") == "value = 2\n"


def test_write_file_rejects_workspace_escape(tmp_path: Path) -> None:
    """write_file cannot write outside the workspace root."""
    tools = build_tool_registry(_workspace(tmp_path))

    result = tools["write_file"].execute({"path": "../outside.txt", "content": "x"})

    assert result.is_error is True
    assert "escapes workspace root" in result.content
    assert not (tmp_path.parent / "outside.txt").exists()


def test_run_shell_uses_filtered_environment_and_reports_timeout(tmp_path: Path) -> None:
    """run_shell filters sensitive env vars and reports command timeout as an error."""
    workspace = _workspace(tmp_path)
    tools = build_tool_registry(workspace)
    os.environ["DEEPSEEK_API_KEY"] = "secret"

    env_result = tools["run_shell"].execute(
        {
            "command": (
                f"{sys.executable} -c "
                '\'import os; print(os.environ.get("DEEPSEEK_API_KEY", "missing"))\''
            )
        }
    )
    timeout_result = tools["run_shell"].execute(
        {
            "command": f"{sys.executable} -c 'import time; time.sleep(2)'",
            "timeout": 1,
        }
    )

    assert env_result.is_error is False
    assert "missing" in env_result.content
    assert "secret" not in env_result.content
    assert timeout_result.is_error is True
    assert "timed out" in timeout_result.content
