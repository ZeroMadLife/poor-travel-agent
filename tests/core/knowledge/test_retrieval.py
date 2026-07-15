from __future__ import annotations

from core.knowledge.parsing import MarkdownParser, ParseRequest
from core.knowledge.retrieval import (
    HashingEmbeddingProvider,
    chunk_document,
    fts_query,
    lexical_terms,
    reciprocal_rank_fusion,
)


def _document(markdown: str):
    return MarkdownParser().parse(
        ParseRequest(
            source_id="src_test",
            relative_path="guide.md",
            source_revision="sha256:test",
            media_type="text/markdown",
            payload=markdown.encode("utf-8"),
        )
    )


def test_heading_aware_chunks_keep_stable_revision_and_block_evidence() -> None:
    document = _document(
        "# Sage\n\n## Context\n\n上下文压缩保留恢复锚点。\n\n## Memory\n\n长期记忆可撤销。\n"
    )
    kwargs = {
        "workspace_id": "knowledge-local",
        "page_id": "page_test",
        "page_revision": "krev_test",
        "page_path": "wiki/sources/guide.md",
        "source_id": "src_test",
        "source_revision": "sha256:test",
        "source_kind": "obsidian",
        "source_relative_path": "guide.md",
        "proposal_id": "kprop_test",
        "artifact_id": "part_test",
        "title": "Sage",
        "visibility": "private",
        "active": True,
    }

    first = chunk_document(document, **kwargs)
    repeated = chunk_document(document, **kwargs)

    assert repeated == first
    assert len(first) == 2
    assert first[0].heading_path == ("Sage", "Context")
    assert first[0].block_id.startswith("pblk_")
    assert first[0].chunk_id.startswith("kchunk_")
    assert first[0].page_revision == "krev_test"
    assert first[0].source_revision == "sha256:test"
    assert first[0].content_hash.startswith("sha256:")


def test_chinese_lexical_projection_and_hashing_embedding_are_deterministic() -> None:
    assert "上下" in lexical_terms("上下文压缩")
    assert '"上下"' in fts_query("上下文压缩")
    provider = HashingEmbeddingProvider(dimensions=64)

    first = provider.embed("上下文压缩 context compaction")
    repeated = provider.embed("上下文压缩 context compaction")

    assert repeated == first
    assert len(first) == 64
    assert abs(sum(value * value for value in first) - 1.0) < 1e-9


def test_rrf_rewards_chunks_found_by_both_retrievers() -> None:
    fused = reciprocal_rank_fusion(
        [("sparse-only", 8.0), ("both", 4.0)],
        [("dense-only", 0.9), ("both", 0.8)],
    )

    assert [item[0] for item in fused] == ["both", "dense-only", "sparse-only"]
    assert fused[0][2:] == (2, 4.0, 2, 0.8)
