from __future__ import annotations

import json

import pytest

from core.loop_harness.errors import LoopBlockedError
from core.loop_harness.worker import CodexFixer, CodexWorker


def _fake_codex(tmp_path, payload: object):
    executable = tmp_path / "codex"
    encoded = json.dumps(json.dumps(payload))
    executable.write_text(
        "#!/bin/sh\n"
        'if [ "${1:-}" = "--version" ]; then echo \'codex-cli test\'; exit 0; fi\n'
        "out=''\n"
        "while [ $# -gt 0 ]; do\n"
        '  if [ "$1" = "--output-last-message" ]; then shift; out=$1; fi\n'
        "  shift\n"
        "done\n"
        f"printf '%s' {encoded} > \"$out\"\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    return executable


def _valid_payload():
    return {
        "verdict": "NO_OP",
        "summary": "no deterministic issue found",
        "evidence": [],
        "reproduction": [],
        "changed_files": [],
        "tests": [],
        "risk_reasons": [],
        "suggested_tier": "C",
        "confidence": 0.8,
    }


def test_worker_uses_temporary_output_and_parses_schema(tmp_path) -> None:
    controller = tmp_path / "controller"
    (controller / "docs/loop-harness").mkdir(parents=True)
    (controller / "core/loop_harness").mkdir(parents=True)
    (controller / "docs/loop-harness/PROMPT.md").write_text("rules", encoding="utf-8")
    (controller / "core/loop_harness/worker_result.schema.json").write_text("{}", encoding="utf-8")
    reports = tmp_path / "reports"
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    worker = CodexWorker(
        codex_bin=_fake_codex(tmp_path, _valid_payload()),
        controller_root=controller,
        reports_root=reports,
        timeout_seconds=10,
    )

    assert worker.probe() == "codex-cli test"
    result = worker.run(
        worktree=worktree,
        run_id="loop-test",
        base_sha="a" * 40,
        scan_scope=("core",),
        protected_paths_digest="b" * 64,
    )

    assert result.verdict == "NO_OP"
    assert list(reports.iterdir()) == []


def test_worker_rejects_non_object_output(tmp_path) -> None:
    controller = tmp_path / "controller"
    (controller / "docs/loop-harness").mkdir(parents=True)
    (controller / "core/loop_harness").mkdir(parents=True)
    (controller / "docs/loop-harness/PROMPT.md").write_text("rules", encoding="utf-8")
    (controller / "core/loop_harness/worker_result.schema.json").write_text("{}", encoding="utf-8")
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    worker = CodexWorker(
        codex_bin=_fake_codex(tmp_path, ["bad"]),
        controller_root=controller,
        reports_root=tmp_path / "reports",
        timeout_seconds=10,
    )

    with pytest.raises(LoopBlockedError) as exc:
        worker.run(
            worktree=worktree,
            run_id="loop-test",
            base_sha="a" * 40,
            scan_scope=("core",),
            protected_paths_digest="b" * 64,
        )
    assert exc.value.code == "BLOCKED_WORKER_OUTPUT"


def test_worker_rejects_out_of_range_confidence(tmp_path) -> None:
    payload = _valid_payload()
    payload["confidence"] = 2
    controller = tmp_path / "controller"
    (controller / "docs/loop-harness").mkdir(parents=True)
    (controller / "core/loop_harness").mkdir(parents=True)
    (controller / "docs/loop-harness/PROMPT.md").write_text("rules", encoding="utf-8")
    (controller / "core/loop_harness/worker_result.schema.json").write_text("{}", encoding="utf-8")
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    worker = CodexWorker(
        codex_bin=_fake_codex(tmp_path, payload),
        controller_root=controller,
        reports_root=tmp_path / "reports",
        timeout_seconds=10,
    )

    with pytest.raises(LoopBlockedError, match="out of range"):
        worker.run(
            worktree=worktree,
            run_id="loop-test",
            base_sha="a" * 40,
            scan_scope=("core",),
            protected_paths_digest="b" * 64,
        )


def test_scanner_accepts_frontend_candidate(tmp_path) -> None:
    payload = _valid_payload()
    payload.update(
        verdict="FRONTEND_CANDIDATE",
        changed_files=["frontend/src/views/KnowledgeView.vue"],
        suggested_tier="A",
    )
    controller = tmp_path / "controller"
    (controller / "docs/loop-harness").mkdir(parents=True)
    (controller / "core/loop_harness").mkdir(parents=True)
    (controller / "docs/loop-harness/PROMPT.md").write_text("rules", encoding="utf-8")
    (controller / "core/loop_harness/worker_result.schema.json").write_text(
        "{}", encoding="utf-8"
    )
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    worker = CodexWorker(
        codex_bin=_fake_codex(tmp_path, payload),
        controller_root=controller,
        reports_root=tmp_path / "reports",
        timeout_seconds=10,
    )

    result = worker.run(
        worktree=worktree,
        run_id="loop-test",
        base_sha="a" * 40,
        scan_scope=("frontend/src",),
        protected_paths_digest="b" * 64,
        phase="SHADOW_SCAN",
    )

    assert result.verdict == "FRONTEND_CANDIDATE"


def test_fixer_uses_workspace_write_and_parses_separate_schema(tmp_path) -> None:
    payload = {
        "summary": "修复知识库空状态间距",
        "changed_files": ["frontend/src/views/KnowledgeView.vue"],
        "tests": ["npm run test -- --run"],
        "risk_reasons": [],
    }
    controller = tmp_path / "controller"
    (controller / "docs/loop-harness").mkdir(parents=True)
    (controller / "core/loop_harness").mkdir(parents=True)
    (controller / "docs/loop-harness/PROMPT.md").write_text("rules", encoding="utf-8")
    (controller / "core/loop_harness/fixer_result.schema.json").write_text(
        "{}", encoding="utf-8"
    )
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    fixer = CodexFixer(
        codex_bin=_fake_codex(tmp_path, payload),
        controller_root=controller,
        reports_root=tmp_path / "reports",
        timeout_seconds=10,
    )

    result = fixer.run(
        worktree=worktree,
        run_id="loop-test",
        base_sha="a" * 40,
        allowed_paths=("frontend/src/views/KnowledgeView.vue",),
        dirty_paths=("frontend/src/views/HumanView.vue",),
        protected_paths_digest="b" * 64,
    )

    assert result.changed_files == ("frontend/src/views/KnowledgeView.vue",)
    assert result.summary == "修复知识库空状态间距"
