"""Benchmark runner for the Sage coding harness.

Drives 10 deterministic scenarios through the real Engine + tool stack using a
ScriptedApiClient (no live LLM). The benchmark is informational: it emits a JSON
and Markdown report under ``evals/coding/results/`` and never gates the build.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Make the repository root importable when run as ``python -m evals.coding.runner``.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.core.coding.scripted_api_client import ScriptedApiClient  # noqa: E402

from core.coding.context import ContextManager, WorkspaceContext  # noqa: E402
from core.coding.engine.engine import Engine  # noqa: E402
from core.coding.memory import MemoryManager  # noqa: E402
from core.coding.tool_executor import (  # noqa: E402
    ApprovalManager,
    PermissionChecker,
    ToolPolicyChecker,
)
from core.coding.tools.base import ToolContext  # noqa: E402
from core.coding.tools.registry import build_tool_registry  # noqa: E402
from evals.coding.assertions import (  # noqa: E402
    assert_approval_requested,
    assert_files_match,
    assert_memory_saved,
    assert_no_write,
    assert_policy_denial,
    assert_tool_calls_match,
)
from evals.coding.metrics import BenchmarkReport, ScenarioResult  # noqa: E402
from evals.coding.scenarios import SCENARIOS, Scenario  # noqa: E402


@dataclass
class _Harness:
    engine: Engine
    workspace: WorkspaceContext
    approval_manager: ApprovalManager | None
    session_id: str
    activated_tools: set[str]


def _permission_mode_for(scenario: Scenario) -> str:
    """Pick the permission mode that exercises the scenario's category."""
    if scenario.category == "policy_boundary" and "plan" in scenario.name:
        return "plan"
    if scenario.category == "policy_boundary":
        return "default"
    if scenario.category == "controlled_edit":
        return "accept_edits"
    return "auto"


def _build_harness(scenario: Scenario, workspace_root: Path, storage_root: Path) -> _Harness:
    """Assemble Engine + tools wired for one scenario."""
    workspace = WorkspaceContext(root=workspace_root)
    activated_tools: set[str] = set()
    # Memory scenarios need a runtime exposing memory_manager to the remember tool.
    memory_manager = MemoryManager(storage_root, workspace.root) if scenario.memory_fact else None
    tool_context = ToolContext(runtime=_FakeRuntime(memory_manager)) if memory_manager else None
    tools = build_tool_registry(
        workspace, tool_context=tool_context, activated_tools=activated_tools
    )
    permission_mode = _permission_mode_for(scenario)
    permission_checker = PermissionChecker(
        permission_mode=permission_mode,
        approval_policy="auto" if permission_mode == "auto" else "",
    )
    policy_checker = ToolPolicyChecker(workspace)

    # The default-mode approval scenario must go through the real approval flow so
    # an ``approval_required`` event is emitted; other scenarios keep it simple.
    approval_manager: ApprovalManager | None = None
    session_id = ""
    if scenario.expected_approval:
        approval_manager = ApprovalManager()
        session_id = f"bench_{scenario.name}"

    engine = Engine(
        model=ScriptedApiClient(scenario.model_responses),
        workspace=workspace,
        tools=tools,
        context_manager=ContextManager(),
        permission_checker=permission_checker,
        policy_checker=policy_checker,
        approval_manager=approval_manager,
        session_id=session_id,
        activated_tools=activated_tools,
        max_steps=20,
    )
    return _Harness(
        engine=engine,
        workspace=workspace,
        approval_manager=approval_manager,
        session_id=session_id,
        activated_tools=activated_tools,
    )


class _FakeRuntime:
    """Minimal runtime stub exposing a MemoryManager to memory tools."""

    def __init__(self, memory_manager: MemoryManager | None) -> None:
        self.memory_manager = memory_manager


async def _run_turn_with_auto_approval(
    harness: _Harness, prompt: str, timeout: float = 30.0
) -> list[dict[str, Any]]:
    """Run a turn, granting any pending approval so the flow is non-blocking.

    Used by the default-mode approval scenario: the engine emits
    ``approval_required`` and then blocks waiting for resolution. We run the turn
    in a task and, in parallel, poll the approval manager for a pending entry and
    resolve it, which unblocks the turn.
    """
    events: list[dict[str, Any]] = []

    async def collect() -> None:
        async for event in harness.engine.run_turn(prompt):
            events.append(event)

    task = asyncio.create_task(collect())

    async def grant() -> None:
        # Wait until the engine submits an approval entry, then grant it once.
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            pending = (
                harness.approval_manager.pending(harness.session_id)
                if harness.approval_manager
                else None
            )
            if pending is not None and harness.approval_manager is not None:
                harness.approval_manager.resolve(harness.session_id, pending["approval_id"], "once")
                return
            await asyncio.sleep(0.02)
        # No approval surfaced within the window; leave the turn to finish/timeout.

    granters = []
    if harness.approval_manager is not None:
        granters.append(asyncio.create_task(grant()))

    try:
        await asyncio.wait_for(task, timeout=timeout)
    except TimeoutError:
        task.cancel()
    finally:
        for g in granters:
            if not g.done():
                g.cancel()
    return events


async def run_scenario(scenario: Scenario) -> ScenarioResult:
    """Run one benchmark scenario and return its result."""
    workspace_dir = tempfile.mkdtemp(prefix=f"sage_bench_{scenario.name}_")
    workspace_root = Path(workspace_dir)
    try:
        for path, content in scenario.workspace_files.items():
            fpath = workspace_root / path
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content, encoding="utf-8")

        # Pin durable-memory storage inside the workspace (.coding/) so the
        # memory assertions can find persisted facts and cleanup is automatic.
        storage_root = workspace_root / ".coding"
        harness = _build_harness(scenario, workspace_root, storage_root)

        start_time = time.monotonic()
        events: list[dict[str, Any]] = []
        try:
            if scenario.expected_approval:
                events = await _run_turn_with_auto_approval(harness, scenario.prompt)
            else:
                async for event in harness.engine.run_turn(scenario.prompt):
                    events.append(event)
        except Exception:  # benchmark must not crash the suite
            pass
        duration_ms = int((time.monotonic() - start_time) * 1000)

        # Run assertions
        passed = True
        detail = ""

        if scenario.expected_no_write and not assert_no_write(events):
            passed = False
            detail = "unexpected write occurred"

        if (
            scenario.expected_files
            and not assert_files_match(workspace_root, scenario.expected_files)
            and not detail
        ):
            passed = False
            detail = "files don't match expected"

        if (
            scenario.expected_tool_calls
            and not assert_tool_calls_match(events, scenario.expected_tool_calls)
            and not detail
        ):
            passed = False
            detail = "tool calls don't match"

        if scenario.expected_denial and not assert_policy_denial(events) and not detail:
            passed = False
            detail = "expected policy denial not found"

        if scenario.expected_approval and not assert_approval_requested(events) and not detail:
            passed = False
            detail = "expected approval not found"

        if (
            scenario.memory_fact
            and not assert_memory_saved(workspace_root, scenario.memory_fact)
            and not detail
        ):
            passed = False
            detail = "memory not saved"

        # Compute metrics
        tool_calls = sum(1 for e in events if e.get("type") == "tool_call")
        tool_errors = sum(1 for e in events if e.get("type") == "tool_result" and e.get("is_error"))
        # A policy-compliant run either expected and saw a denial, or never
        # triggered an unexpected denial.
        policy_compliant = True
        if scenario.expected_denial:
            policy_compliant = assert_policy_denial(events)
        else:
            policy_compliant = not any(
                e.get("type") == "tool_result"
                and e.get("is_error")
                and any(
                    marker in str(e.get("content", ""))
                    for marker in ("plan_mode", "prior_read_required")
                )
                for e in events
            )

        return ScenarioResult(
            name=scenario.name,
            category=scenario.category,
            passed=passed,
            tool_calls=tool_calls,
            tool_errors=tool_errors,
            policy_compliant=policy_compliant,
            duration_ms=duration_ms,
            detail=detail,
        )
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


async def run_benchmark() -> BenchmarkReport:
    """Run all benchmark scenarios and return a report."""
    report = BenchmarkReport()
    # Each scenario owns its isolated workspace (with .coding/ storage inside),
    # so no shared storage root is needed.
    for scenario in SCENARIOS:
        result = await run_scenario(scenario)
        report.results.append(result)
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] {result.name} ({result.category}) - {result.detail or 'ok'}")
    return report


def _write_reports(report: BenchmarkReport) -> tuple[Path, Path]:
    results_dir = Path("evals/coding/results")
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    results_dir.mkdir(parents=True, exist_ok=True)
    d = report.to_dict()

    json_path = results_dir / f"{timestamp}-report.json"
    json_path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [f"# Sage V6 Benchmark Report ({timestamp})", "", "## Metrics"]
    for key, value in d["metrics"].items():
        md_lines.append(f"- **{key}**: {value}")
    md_lines.append("")
    md_lines.append("## Results")
    md_lines.append("| Scenario | Category | Status | Tool Calls | Duration | Detail |")
    md_lines.append("|----------|----------|--------|------------|----------|--------|")
    for r in d["results"]:
        md_lines.append(
            f"| {r['name']} | {r['category']} | {'PASS' if r['passed'] else 'FAIL'} "
            f"| {r['tool_calls']} | {r['duration_ms']}ms | {r['detail']} |"
        )
    md_path = results_dir / f"{timestamp}-report.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return json_path, md_path


def main() -> None:
    """Run the benchmark and save results."""
    print("Sage V6 Benchmark")
    print("=" * 60)
    report = asyncio.run(run_benchmark())
    print()
    print("Metrics:")
    d = report.to_dict()
    for key, value in d["metrics"].items():
        print(f"  {key}: {value}")
    print()

    json_path, md_path = _write_reports(report)
    print(f"Report saved to {json_path} and {md_path}")


if __name__ == "__main__":
    main()
