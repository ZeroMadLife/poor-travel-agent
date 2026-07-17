"""Checkpoint command plumbing for the reusable harness runtime."""

from __future__ import annotations

import asyncio
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from sage_harness.config import HarnessRunContext
from sage_harness.runtime.manager import HarnessRunManager, HarnessRunRequest
from typing_extensions import TypedDict


class RecordingGraph:
    def __init__(self) -> None:
        self.inputs: list[Any] = []

    async def astream(self, input, *, config, context, stream_mode):  # type: ignore[no-untyped-def]
        self.inputs.append(input)
        yield ("custom", {"type": "agent_started"})


def _context(run_id: str) -> HarnessRunContext:
    return HarnessRunContext(
        thread_id="thread-1",
        run_id=run_id,
        workspace_id="workspace-1",
        workspace_path="/tmp/workspace",
    )


def _request(*, resume: bool = False) -> HarnessRunRequest:
    return HarnessRunRequest(
        thread_id="thread-1",
        run_id="run-1",
        context=_context("run-1"),
        message="" if resume else "continue",
        resume=resume,
        resume_value={"choice": "once"} if resume else None,
    )


def test_manager_uses_server_owned_command_for_checkpoint_resume() -> None:
    graph = RecordingGraph()

    async def run() -> None:
        items = [item async for item in HarnessRunManager(graph).stream(_request(resume=True))]
        assert items[0].mode == "custom"

    asyncio.run(run())

    command = graph.inputs[0]
    assert command.__class__.__name__ == "Command"
    assert command.resume == {"choice": "once"}


def test_resume_request_can_omit_a_new_user_message() -> None:
    request = _request(resume=True)
    assert request.message == ""


def test_request_rejects_a_cross_run_context() -> None:
    try:
        HarnessRunRequest(
            thread_id="thread-1",
            run_id="run-2",
            context=_context("run-1"),
            message="continue",
        )
    except ValueError as exc:
        assert str(exc) == "run context run_id does not match request"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("cross-run context must be rejected")


class _InterruptState(TypedDict, total=False):
    decision: str


def test_manager_resumes_a_real_checkpointed_graph_interrupt() -> None:
    def wait_for_decision(state: _InterruptState) -> _InterruptState:
        decision = interrupt({"type": "approval_required", "tool": "write_file"})
        return {"decision": str(decision)}

    graph = StateGraph(_InterruptState)
    graph.add_node("wait", wait_for_decision)
    graph.add_edge(START, "wait")
    graph.add_edge("wait", END)
    compiled = graph.compile(checkpointer=InMemorySaver())
    manager = HarnessRunManager(compiled)

    async def run() -> tuple[list[Any], list[Any]]:
        first = [
            item
            async for item in manager.stream(
                HarnessRunRequest(
                    thread_id="thread-1",
                    run_id="run-1",
                    context=_context("run-1"),
                    message="start",
                )
            )
        ]
        resumed = [
            item
            async for item in manager.stream(
                HarnessRunRequest(
                    thread_id="thread-1",
                    run_id="run-2",
                    context=_context("run-2"),
                    message="",
                    resume=True,
                    resume_value="once",
                )
            )
        ]
        return first, resumed

    first, resumed = asyncio.run(run())
    first_values = [item.payload for item in first if item.mode == "values"]
    resumed_values = [item.payload for item in resumed if item.mode == "values"]
    assert any("__interrupt__" in value for value in first_values)
    assert resumed_values[-1]["decision"] == "once"
