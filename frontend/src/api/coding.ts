import type { CodingSessionResponse } from '../types/api'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || window.location.origin

export async function startCodingSession(workspaceRoot?: string): Promise<CodingSessionResponse> {
  const response = await fetch(new URL('/api/v1/coding/session', API_BASE_URL), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workspace_root: workspaceRoot || null }),
  })

  if (!response.ok) {
    throw new Error(`Coding session request failed with status ${response.status}`)
  }

  return (await response.json()) as CodingSessionResponse
}

export function buildCodingStreamUrl(sessionId: string): string {
  const base = new URL(API_BASE_URL, window.location.origin)
  base.protocol = base.protocol === 'https:' ? 'wss:' : 'ws:'
  base.pathname = `/api/v1/coding/${sessionId}/stream`
  base.search = ''
  return base.toString()
}
