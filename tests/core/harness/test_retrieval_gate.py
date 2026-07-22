"""Deterministic H2.8 retrieval routing and public receipts."""

from sage_harness import MemoryReference, MemoryRetrievalResult

from core.coding.run_coordinator import RunEvent
from core.harness.retrieval_gate import (
    decide_retrieval_gate,
    memory_retrieval_events,
    retrieval_source_event,
    retrieval_sources_from_events,
)


def test_fast_chat_skips_retrieval_without_leaking_query() -> None:
    receipt = decide_retrieval_gate(
        "1 + 1 等于多少？",
        memory_available=True,
        knowledge_available=True,
        web_available=True,
    )

    payload = receipt.to_payload(run_id="run-1")
    assert receipt.decision == "skip"
    assert receipt.reason_code == "no_retrieval_signal"
    assert payload["actual_hit_count"] == 0
    assert "1 + 1" not in repr(payload)
    assert len(receipt.query_fingerprint) == 16


def test_explicit_sources_select_mixed_and_degrade_truthfully() -> None:
    receipt = decide_retrieval_gate(
        "结合我的知识库和官网最新资料解释 LangGraph checkpoint",
        memory_available=True,
        knowledge_available=True,
        web_available=False,
    )

    assert receipt.decision == "knowledge"
    assert receipt.candidate_sources == ("knowledge", "web")
    assert receipt.selected_sources == ("knowledge",)
    assert receipt.degraded is True
    assert receipt.token_budget_by_source == {"knowledge": 3_000}


def test_memory_signal_selects_only_approved_memory_channel() -> None:
    receipt = decide_retrieval_gate(
        "你还记得我之前告诉过你的个人偏好吗？",
        memory_available=True,
        knowledge_available=False,
        web_available=False,
    )

    assert receipt.decision == "semantic_memory"
    assert receipt.memory_selected is True
    assert receipt.selected_sources == ("semantic_memory",)


def test_frozen_knowledge_selection_routes_to_knowledge() -> None:
    receipt = decide_retrieval_gate(
        "帮我解释这里",
        surface_context={
            "selection": {"type": "graph_node", "id": "node-1"},
            "graph_revision": "graph-7",
        },
        memory_available=True,
        knowledge_available=True,
        web_available=False,
    )

    assert receipt.decision == "knowledge"
    assert receipt.reason_code == "explicit_source_signal"


def test_knowledge_retrieval_word_routes_to_knowledge() -> None:
    receipt = decide_retrieval_gate(
        "检索 Phoenix checkpoint 的当前修订证据",
        memory_available=True,
        knowledge_available=True,
        web_available=True,
    )

    assert receipt.decision == "knowledge"
    assert receipt.selected_sources == ("knowledge",)


def test_retrieval_result_projects_actual_hits_without_content() -> None:
    event = RunEvent(
        kind="tool",
        status="completed",
        payload={
            "type": "tool_result",
            "tool": "knowledge_search",
            "content": (
                '{"status":"evidence_found","used_tokens":120,"token_budget":3000,'
                '"omitted_count":2,"citations":[{"citation_id":"secret"}]}'
            ),
        },
        event_id="tool-result-1",
    )

    projected = retrieval_source_event(event, run_id="run-1")

    assert projected is not None
    assert projected.payload == {
        "type": "retrieval_source_completed",
        "version": 1,
        "run_id": "run-1",
        "source": "knowledge",
        "status": "evidence_found",
        "actual_hit_count": 1,
        "used_tokens": 120,
        "token_budget": 3000,
        "omitted_count": 2,
    }
    assert "secret" not in repr(projected.payload)


def test_memory_retrieval_projects_per_source_receipts_without_content() -> None:
    result = MemoryRetrievalResult(
        references=(
            MemoryReference(
                memory_id="memory-secret",
                summary="private preference",
                metadata={"memory_kind": "semantic"},
            ),
        ),
        token_budget_by_source={"semantic_memory": 1200, "episodic_memory": 1600},
        used_tokens_by_source={"semantic_memory": 12, "episodic_memory": 0},
        omitted_count_by_source={"semantic_memory": 1, "episodic_memory": 0},
    )

    events = memory_retrieval_events(result, run_id="run-1")

    assert [event.payload["source"] for event in events] == [
        "semantic_memory",
        "episodic_memory",
    ]
    assert events[0].payload["status"] == "evidence_found"
    assert events[0].payload["actual_hit_count"] == 1
    assert events[1].payload["status"] == "no_evidence"
    assert "private preference" not in repr(events)


def test_retrieval_sources_restore_explicit_skip_and_legacy_absence() -> None:
    skip = RunEvent(
        kind="harness",
        status="completed",
        payload={
            "type": "retrieval_gate_decided",
            "selected_sources": [],
        },
    )
    mixed = RunEvent(
        kind="harness",
        status="completed",
        payload={
            "type": "retrieval_gate_decided",
            "selected_sources": ["knowledge", "web", "forged"],
        },
    )

    assert retrieval_sources_from_events(()) is None
    assert retrieval_sources_from_events((skip,)) == frozenset()
    assert retrieval_sources_from_events((skip, mixed)) == frozenset({"knowledge", "web"})
