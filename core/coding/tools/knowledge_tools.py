"""Evidence-only knowledge retrieval for the coding harness."""

from __future__ import annotations

import json
from typing import Any

from core.coding.context import WorkspaceContext
from core.coding.tools.base import ToolContext, ToolResult
from core.coding.tools.registry import register_tool
from core.coding.tools.schemas import KnowledgeSearchArgs
from core.knowledge import KnowledgeStore


@register_tool(
    name="knowledge_search",
    description=(
        "Search approved Sage knowledge and return revision-bound citations. "
        "When status is no_evidence, do not claim the answer came from the knowledge base."
    ),
    schema={"query": "str", "top_k": "int=8", "token_budget": "int=3000"},
    schema_model=KnowledgeSearchArgs,
    risky=False,
    category="knowledge",
    requires_approval=False,
    timeout=30.0,
    deferred=False,
)
def knowledge_search(
    workspace: WorkspaceContext,
    args: dict[str, Any],
    tool_context: ToolContext | None = None,
) -> ToolResult:
    """Retrieve bounded evidence without exposing server filesystem paths."""

    _ = workspace
    store = tool_context.knowledge_store if tool_context is not None else None
    if not isinstance(store, KnowledgeStore):
        return ToolResult(
            content=json.dumps(
                {
                    "status": "unavailable",
                    "message": "knowledge workspace is not configured",
                    "citations": [],
                },
                ensure_ascii=False,
            ),
            is_error=True,
        )
    bundle = store.retrieve(
        str(args["query"]),
        top_k=int(args["top_k"]),
        token_budget=int(args["token_budget"]),
    )
    payload = {
        "status": bundle.status,
        "query": bundle.query,
        "used_tokens": bundle.used_tokens,
        "token_budget": bundle.token_budget,
        "omitted_count": bundle.omitted_count,
        "instruction": (
            "Use only the cited excerpts for knowledge-base claims."
            if bundle.evidence
            else "The knowledge base has no evidence for this query. Say so explicitly."
        ),
        "citations": [
            {
                "citation_id": evidence.hit.citation_id,
                "rank": evidence.hit.rank,
                "page_revision": evidence.hit.chunk.page_revision,
                "source_revision": evidence.hit.chunk.source_revision,
                "source_kind": evidence.hit.chunk.source_kind,
                "source_relative_path": evidence.hit.chunk.source_relative_path,
                "title": evidence.hit.chunk.title,
                "heading_path": list(evidence.hit.chunk.heading_path),
                "block_id": evidence.hit.chunk.block_id,
                "excerpt": evidence.excerpt,
                "truncated": evidence.truncated,
            }
            for evidence in bundle.evidence
        ],
    }
    return ToolResult(content=json.dumps(payload, ensure_ascii=False, indent=2))
