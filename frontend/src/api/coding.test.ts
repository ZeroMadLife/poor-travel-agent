import { afterEach, describe, expect, it, vi } from 'vitest'
import { buildCodingStreamUrl, startCodingSession } from './coding'

describe('coding API client', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('creates a coding session', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ session_id: 'c1', workspace_root: '/tmp/repo' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const response = await startCodingSession('/tmp/repo')

    expect(response.session_id).toBe('c1')
    expect(fetchMock).toHaveBeenCalledWith(expect.any(URL), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workspace_root: '/tmp/repo' }),
    })
  })

  it('builds a websocket URL for coding streams', () => {
    const url = buildCodingStreamUrl('c1')

    expect(url).toContain('/api/v1/coding/c1/stream')
    expect(url.startsWith('ws')).toBe(true)
  })
})
