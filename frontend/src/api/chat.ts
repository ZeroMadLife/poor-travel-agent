import type {
  ChatStartResponse,
  ItineraryListResponse,
  SessionListResponse,
  SessionMessagesResponse,
} from '../types/api'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || window.location.origin

export async function startChat(content: string, userId = 'anonymous'): Promise<ChatStartResponse> {
  const response = await fetch(new URL('/api/v1/chat', API_BASE_URL), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, user_id: userId }),
  })

  if (!response.ok) {
    throw new Error(`Chat request failed with status ${response.status}`)
  }

  return (await response.json()) as ChatStartResponse
}

export function buildChatStreamUrl(sessionId: string): string {
  const base = new URL(API_BASE_URL, window.location.origin)
  base.protocol = base.protocol === 'https:' ? 'wss:' : 'ws:'
  base.pathname = `/api/v1/chat/${sessionId}/stream`
  base.search = ''
  return base.toString()
}

export async function listSessions(userId: string): Promise<SessionListResponse> {
  const url = new URL('/api/v1/sessions', API_BASE_URL)
  url.searchParams.set('user_id', userId)
  const response = await fetch(url.toString())
  if (!response.ok) {
    throw new Error(`Session list request failed with status ${response.status}`)
  }
  return (await response.json()) as SessionListResponse
}

export async function getSessionMessages(sessionId: string): Promise<SessionMessagesResponse> {
  const response = await fetch(new URL(`/api/v1/sessions/${sessionId}/messages`, API_BASE_URL))
  if (!response.ok) {
    throw new Error(`Session messages request failed with status ${response.status}`)
  }
  return (await response.json()) as SessionMessagesResponse
}

export async function getSessionItineraries(sessionId: string): Promise<ItineraryListResponse> {
  const response = await fetch(new URL(`/api/v1/sessions/${sessionId}/itineraries`, API_BASE_URL))
  if (!response.ok) {
    throw new Error(`Session itineraries request failed with status ${response.status}`)
  }
  return (await response.json()) as ItineraryListResponse
}

export async function listItineraries(userId: string): Promise<ItineraryListResponse> {
  const url = new URL('/api/v1/itineraries', API_BASE_URL)
  url.searchParams.set('user_id', userId)
  const response = await fetch(url.toString())
  if (!response.ok) {
    throw new Error(`Itinerary list request failed with status ${response.status}`)
  }
  return (await response.json()) as ItineraryListResponse
}
