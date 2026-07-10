"""Tests for the coding-harness benchmark runner and metrics."""

from __future__ import annotations

import asyncio

from evals.coding.metrics import BenchmarkReport, ScenarioResult
from evals.coding.runner import run_benchmark, run_scenario
from evals.coding.scenarios import SCENARIOS


async def test_benchmark_scenarios_run() -> None:
    """All 10 scenarios run to completion without raising.

    This is a smoke test: it does not assert pass/fail, only that every scenario
    produces a ScenarioResult. Failure details surface in the result.detail field.
    """
    results = [await run_scenario(scenario) for scenario in SCENARIOS]

    assert len(results) == 10
    names = {r.name for r in results}
    assert names == {scenario.name for scenario in SCENARIOS}
    # Every result has a populated category and non-negative counts.
    for result in results:
        assert result.category in {
            "read_explain",
            "controlled_edit",
            "policy_boundary",
            "memory_continuity",
        }
        assert result.tool_calls >= 0
        assert result.tool_errors >= 0
        assert result.duration_ms >= 0
        assert isinstance(result.detail, str)


async def test_run_benchmark_returns_full_report() -> None:
    """The full benchmark run covers all scenarios and aggregates metrics."""
    report = await run_benchmark()

    assert len(report.results) == 10
    metrics = report.to_dict()["metrics"]
    # All four headline metrics are present and in valid ranges.
    assert 0.0 <= metrics["task_completion_rate"] <= 1.0
    assert 0.0 <= metrics["tool_call_success_rate"] <= 1.0
    assert 0.0 <= metrics["policy_compliance_rate"] <= 1.0
    assert metrics["p95_turn_latency_ms"] >= 0


def test_metrics_calculation() -> None:
    """BenchmarkReport metric math is correct for a known input."""
    report = BenchmarkReport(
        results=[
            ScenarioResult(
                name="a",
                category="read_explain",
                passed=True,
                tool_calls=3,
                tool_errors=0,
                policy_compliant=True,
                duration_ms=100,
            ),
            ScenarioResult(
                name="b",
                category="controlled_edit",
                passed=False,
                tool_calls=2,
                tool_errors=1,
                policy_compliant=True,
                duration_ms=200,
            ),
            ScenarioResult(
                name="c",
                category="policy_boundary",
                passed=True,
                tool_calls=1,
                tool_errors=0,
                policy_compliant=False,
                duration_ms=300,
            ),
            ScenarioResult(
                name="d",
                category="memory_continuity",
                passed=True,
                tool_calls=2,
                tool_errors=0,
                policy_compliant=True,
                duration_ms=400,
            ),
        ]
    )

    # 3 of 4 passed.
    assert report.task_completion_rate == 0.75
    # 8 total tool calls, 1 error -> 7/8.
    assert report.tool_call_success_rate == 0.875
    # 3 of 4 policy-compliant.
    assert report.policy_compliance_rate == 0.75
    # latencies sorted: [100, 200, 300, 400]; idx = int(4*0.95)=3 -> 400.
    assert report.p95_turn_latency_ms == 400


def test_metrics_empty_report() -> None:
    """An empty report degrades to safe defaults rather than raising."""
    report = BenchmarkReport()
    assert report.task_completion_rate == 0.0
    # No tool calls means success rate is vacuously 1.0.
    assert report.tool_call_success_rate == 1.0
    assert report.policy_compliance_rate == 1.0
    assert report.p95_turn_latency_ms == 0.0
    d = report.to_dict()
    assert d["metrics"]["task_completion_rate"] == 0.0
    assert d["results"] == []


def test_metrics_single_result_latency() -> None:
    """p95 over one result returns that result's latency."""
    report = BenchmarkReport(
        results=[
            ScenarioResult(
                name="solo",
                category="read_explain",
                passed=True,
                duration_ms=123,
            )
        ]
    )
    assert report.p95_turn_latency_ms == 123


def test_benchmark_is_informational() -> None:
    """The benchmark runner never raises on assertion failures (smoke guard).

    Mirrors the contract stated in the harness design: the benchmark reports
    pass/fail per scenario but does not gate the build. We simulate a failing
    assertion path by running the suite; the test passes as long as no exception
    escapes.
    """
    report = asyncio.run(run_benchmark())
    assert len(report.results) == 10
    # at least one result must carry a category, regardless of pass state.
    assert all(r.category for r in report.results)
