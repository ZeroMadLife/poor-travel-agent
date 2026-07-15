"""Local V7.2 Knowledge Workspace review and rollback routes."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from api.schemas import (
    KnowledgeIngestRequest,
    KnowledgePageResponse,
    KnowledgePagesResponse,
    KnowledgeProposalDetailResponse,
    KnowledgeProposalEvent,
    KnowledgeProposalResponse,
    KnowledgeProposalsResponse,
    KnowledgeRollbackRequest,
    KnowledgeSourceRootSummary,
    KnowledgeTransitionRequest,
    KnowledgeWorkspaceSummary,
)
from core.knowledge import (
    KnowledgeConflictError,
    KnowledgePage,
    KnowledgeProjectionError,
    KnowledgeProposal,
    KnowledgeStore,
)

router = APIRouter()
_MAX_DIFF_CHARS = 200_000


@router.get("/api/v1/knowledge", response_model=KnowledgeWorkspaceSummary)
async def get_knowledge_summary(
    request: Request, response: Response
) -> KnowledgeWorkspaceSummary:
    store = _require_store(request)
    summary = store.summary()
    response.headers["Cache-Control"] = "no-store"
    return KnowledgeWorkspaceSummary(
        status="ready",
        workspace_name=summary.workspace_name,
        source_count=summary.source_count,
        wiki_page_count=summary.wiki_page_count,
        pending_proposal_count=summary.pending_proposal_count,
        last_synced_at=summary.last_synced_at,
        source_roots=[
            KnowledgeSourceRootSummary(
                root_id=item.root_id,
                kind=item.kind,  # type: ignore[arg-type]
                label=item.label,
            )
            for item in summary.source_roots
        ],
    )


@router.post(
    "/api/v1/knowledge/ingest",
    response_model=KnowledgeProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_knowledge_source(
    payload: KnowledgeIngestRequest, request: Request
) -> KnowledgeProposalResponse:
    store = _require_store(request)
    try:
        proposal = store.ingest(payload.source_root_id, payload.relative_path)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="knowledge source root not found") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="knowledge source not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KnowledgeConflictError as exc:
        raise HTTPException(status_code=409, detail="knowledge source conflict") from exc
    return _proposal_response(store, proposal)


@router.get(
    "/api/v1/knowledge/proposals", response_model=KnowledgeProposalsResponse
)
async def list_knowledge_proposals(
    request: Request,
    proposal_status: Literal["pending", "approved", "rejected"] | None = Query(
        default=None, alias="status"
    ),
) -> KnowledgeProposalsResponse:
    store = _require_store(request)
    return KnowledgeProposalsResponse(
        proposals=[
            _proposal_response(store, proposal)
            for proposal in store.list_proposals(proposal_status)
        ]
    )


@router.get(
    "/api/v1/knowledge/proposals/{proposal_id}",
    response_model=KnowledgeProposalDetailResponse,
)
async def get_knowledge_proposal(
    proposal_id: str, request: Request
) -> KnowledgeProposalDetailResponse:
    store = _require_store(request)
    try:
        proposal = store.get_proposal(proposal_id)
        events = store.list_events(proposal_id)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="knowledge proposal not found") from exc
    return KnowledgeProposalDetailResponse(
        proposal=_proposal_response(store, proposal),
        events=[
            KnowledgeProposalEvent(
                event_id=event.event_id,
                event_type=event.event_type,
                revision=event.revision,
                detail=event.detail,
                created_at=event.created_at,
            )
            for event in events
        ],
    )


@router.post(
    "/api/v1/knowledge/proposals/{proposal_id}/approve",
    response_model=KnowledgeProposalResponse,
)
async def approve_knowledge_proposal(
    proposal_id: str, payload: KnowledgeTransitionRequest, request: Request
) -> KnowledgeProposalResponse:
    store = _require_store(request)
    try:
        proposal = store.approve(proposal_id, payload.expected_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="knowledge proposal not found") from exc
    except KnowledgeConflictError as exc:
        raise HTTPException(status_code=409, detail="knowledge revision conflict") from exc
    except KnowledgeProjectionError as exc:
        raise HTTPException(status_code=500, detail="knowledge projection failed") from exc
    return _proposal_response(store, proposal)


@router.post(
    "/api/v1/knowledge/proposals/{proposal_id}/reject",
    response_model=KnowledgeProposalResponse,
)
async def reject_knowledge_proposal(
    proposal_id: str, payload: KnowledgeTransitionRequest, request: Request
) -> KnowledgeProposalResponse:
    store = _require_store(request)
    try:
        proposal = store.reject(proposal_id, payload.expected_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="knowledge proposal not found") from exc
    except KnowledgeConflictError as exc:
        raise HTTPException(status_code=409, detail="knowledge revision conflict") from exc
    return _proposal_response(store, proposal)


@router.get("/api/v1/knowledge/pages", response_model=KnowledgePagesResponse)
async def list_knowledge_pages(request: Request) -> KnowledgePagesResponse:
    store = _require_store(request)
    return KnowledgePagesResponse(
        pages=[_page_response(page) for page in store.list_pages()]
    )


@router.post(
    "/api/v1/knowledge/pages/{page_id}/rollback",
    response_model=KnowledgeProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def propose_knowledge_rollback(
    page_id: str, payload: KnowledgeRollbackRequest, request: Request
) -> KnowledgeProposalResponse:
    store = _require_store(request)
    try:
        proposal = store.propose_rollback(
            page_id,
            target_revision_id=payload.target_revision_id,
            expected_page_revision=payload.expected_page_revision,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="knowledge page revision not found") from exc
    except (ValueError, KnowledgeConflictError) as exc:
        raise HTTPException(status_code=409, detail="knowledge revision conflict") from exc
    return _proposal_response(store, proposal)


def _require_store(request: Request) -> KnowledgeStore:
    if str(getattr(request.app.state, "cloud_app_env", "development")) == "production":
        raise HTTPException(
            status_code=503,
            detail="knowledge workspace requires tenant isolation before cloud use",
        )
    store = getattr(request.app.state, "knowledge_store", None)
    if not isinstance(store, KnowledgeStore):
        raise HTTPException(status_code=503, detail="knowledge workspace is not configured")
    return store


def _proposal_response(
    store: KnowledgeStore, proposal: KnowledgeProposal
) -> KnowledgeProposalResponse:
    diff = store.proposal_diff(proposal)
    truncated = len(diff) > _MAX_DIFF_CHARS
    if truncated:
        diff = diff[:_MAX_DIFF_CHARS] + "\n... diff truncated ...\n"
    return KnowledgeProposalResponse(
        proposal_id=proposal.proposal_id,
        source_root_id=proposal.source_root_id,
        source_kind=proposal.source_kind,
        source_relative_path=proposal.source_relative_path,
        source_revision=proposal.source_revision,
        raw_path=proposal.raw_path,
        page_id=proposal.page_id,
        target_path=proposal.target_path,
        title=proposal.title,
        base_page_revision=proposal.base_page_revision,
        change_kind=proposal.change_kind,  # type: ignore[arg-type]
        status=proposal.status,  # type: ignore[arg-type]
        projection_status=proposal.projection_status,  # type: ignore[arg-type]
        revision=proposal.revision,
        error=proposal.error,
        diff=diff,
        diff_truncated=truncated,
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
    )


def _page_response(page: KnowledgePage) -> KnowledgePageResponse:
    return KnowledgePageResponse.model_validate(
        {
            "page_id": page.page_id,
            "path": page.path,
            "title": page.title,
            "current_revision": page.current_revision,
            "updated_at": page.updated_at,
            "revisions": [
                {
                    "revision_id": revision.revision_id,
                    "sequence": revision.sequence,
                    "content_hash": revision.content_hash,
                    "source_revision": revision.source_revision,
                    "proposal_id": revision.proposal_id,
                    "change_kind": revision.change_kind,
                    "git_commit": revision.git_commit,
                    "created_at": revision.created_at,
                }
                for revision in page.revisions
            ],
        }
    )
