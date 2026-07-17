"""Long-running LangGraph invocation manager."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar, Protocol

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from sage_harness.config import HarnessRunContext
from sage_harness.runtime.checkpoint import thread_config
from sage_harness.runtime.events import HarnessStreamItem, normalize_stream_item


class StreamableGraph(Protocol):
    """Subset of CompiledStateGraph required by the runtime manager."""

    def astream(
        self,
        input: Any,
        *,
        config: Mapping[str, Any],
        context: HarnessRunContext,
        stream_mode: list[str],
    ) -> AsyncIterator[Any]: ...


@dataclass(frozen=True, slots=True)
class HarnessRunRequest:
    """Server-owned input for one graph run."""

    thread_id: str
    run_id: str
    context: HarnessRunContext
    message: str
    recursion_limit: int = 100
    metadata: Mapping[str, object] = field(default_factory=dict)
    state_update: Mapping[str, object] = field(default_factory=dict)
    resume: bool = False
    resume_value: object | None = None

    def __post_init__(self) -> None:
        if not str(self.run_id).strip():
            raise ValueError("run_id must not be empty")
        if not self.resume and not str(self.message).strip():
            raise ValueError("message must not be empty")
        if self.context.thread_id != self.thread_id:
            raise ValueError("run context thread_id does not match request")
        if self.context.run_id != self.run_id:
            raise ValueError("run context run_id does not match request")
        message_updates = self.state_update.get("messages")
        if message_updates is not None and not isinstance(message_updates, list | tuple):
            raise ValueError("state_update messages must be a list or tuple")


class HarnessRunManager:
    """Own graph invocation configuration while Sage owns durable run leases."""

    STREAM_MODES: ClassVar[list[str]] = ["values", "messages", "custom"]

    def __init__(self, graph: StreamableGraph) -> None:
        self.graph = graph

    async def stream(self, request: HarnessRunRequest) -> AsyncIterator[HarnessStreamItem]:
        """Stream graph values/messages/custom events in deterministic order."""
        config = thread_config(request.thread_id, recursion_limit=request.recursion_limit)
        if request.metadata:
            config["metadata"] = dict(request.metadata)
        if request.resume:
            graph_input: Any = Command(resume=request.resume_value)
        else:
            state = dict(request.state_update)
            message_updates = state.pop("messages", ())
            prior_updates = (
                list(message_updates) if isinstance(message_updates, list | tuple) else []
            )
            state["messages"] = [
                *prior_updates,
                HumanMessage(content=request.message, id=f"harness:{request.run_id}:user"),
            ]
            graph_input = state
        sequence = 0
        async for raw in self.graph.astream(
            graph_input,
            config=config,
            context=request.context,
            stream_mode=self.STREAM_MODES,
        ):
            sequence += 1
            yield normalize_stream_item(raw, sequence)


__all__ = ["HarnessRunManager", "HarnessRunRequest"]
