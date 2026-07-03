import { afterEach, describe, expect, it, vi } from 'vitest'
import { getSessionMessages, listSessions } from './chat'

describe('history API client', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('loads sessions for a user', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ sessions: [{ session_id: 's1', title: '杭州' }] }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const response = await listSessions('u_1')

    expect(response.sessions[0].session_id).toBe('s1')
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/v1/sessions?user_id=u_1'))
  })

  it('loads persisted messages for a session', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ messages: [{ role: 'user', content: '你好' }] }),
      }),
    )

    const response = await getSessionMessages('s1')

    expect(response.messages[0].content).toBe('你好')
  })
})
