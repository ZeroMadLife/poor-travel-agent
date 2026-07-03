import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useSessionStore } from './session'

const listSessionsMock = vi.fn()
const getSessionMessagesMock = vi.fn()

vi.mock('../api/chat', () => ({
  listSessions: (...args: unknown[]) => listSessionsMock(...args),
  getSessionMessages: (...args: unknown[]) => getSessionMessagesMock(...args),
}))

describe('session store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    listSessionsMock.mockReset()
    getSessionMessagesMock.mockReset()
  })

  it('loads session summaries for a user', async () => {
    listSessionsMock.mockResolvedValue({
      sessions: [
        {
          session_id: 's1',
          title: '杭州2日游',
          created_at: '2026-07-03T00:00:00',
          updated_at: '2026-07-03T00:00:00',
          status: 'active',
        },
      ],
    })
    const store = useSessionStore()

    await store.loadSessions('u_1')

    expect(store.sessions[0].title).toBe('杭州2日游')
    expect(listSessionsMock).toHaveBeenCalledWith('u_1')
  })

  it('selects a session and loads its messages', async () => {
    getSessionMessagesMock.mockResolvedValue({
      messages: [{ role: 'user', content: '你好', tool_calls: null, created_at: 'now' }],
    })
    const store = useSessionStore()

    await store.selectSession('s1')

    expect(store.activeSessionId).toBe('s1')
    expect(store.messages[0].content).toBe('你好')
  })
})
