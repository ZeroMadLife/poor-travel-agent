import type {
  KnowledgePage,
  KnowledgeProposal,
  KnowledgeWorkspaceSummary,
} from '../types/api'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || window.location.origin

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(new URL(path, API_BASE_URL), {
    credentials: 'include',
    ...init,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null
    throw new Error(body?.detail || `知识库请求失败：${response.status}`)
  }
  return (await response.json()) as T
}

export function fetchKnowledgeSummary(): Promise<KnowledgeWorkspaceSummary> {
  return request('/api/v1/knowledge')
}

export function fetchKnowledgeProposals(status = 'pending'): Promise<KnowledgeProposal[]> {
  const url = new URL('/api/v1/knowledge/proposals', API_BASE_URL)
  url.searchParams.set('status', status)
  return request<{ proposals: KnowledgeProposal[] }>(`${url.pathname}${url.search}`)
    .then((response) => response.proposals)
}

export function fetchKnowledgePages(): Promise<KnowledgePage[]> {
  return request<{ pages: KnowledgePage[] }>('/api/v1/knowledge/pages')
    .then((response) => response.pages)
}

export function ingestKnowledgeSource(
  sourceRootId: string,
  relativePath: string,
): Promise<KnowledgeProposal> {
  return request('/api/v1/knowledge/ingest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_root_id: sourceRootId, relative_path: relativePath }),
  })
}

export function transitionKnowledgeProposal(
  proposalId: string,
  action: 'approve' | 'reject',
  expectedRevision: number,
): Promise<KnowledgeProposal> {
  return request(`/api/v1/knowledge/proposals/${encodeURIComponent(proposalId)}/${action}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ expected_revision: expectedRevision }),
  })
}

export function proposeKnowledgeRollback(
  pageId: string,
  targetRevisionId: string,
  expectedPageRevision: string,
): Promise<KnowledgeProposal> {
  return request(`/api/v1/knowledge/pages/${encodeURIComponent(pageId)}/rollback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      target_revision_id: targetRevisionId,
      expected_page_revision: expectedPageRevision,
    }),
  })
}
