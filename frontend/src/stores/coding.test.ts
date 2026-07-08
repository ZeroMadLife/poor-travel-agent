import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useCodingStore } from './coding'

describe('coding store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('has correct initial state', () => {
    const store = useCodingStore()
    expect(store.sessionId).toBe('')
    expect(store.messages).toEqual([])
    expect(store.isThinking).toBe(false)
    expect(store.skills).toEqual([])
    expect(store.contextBudget).toBe(60000)
  })

  it('computes context percent from chars', () => {
    const store = useCodingStore()
    store.contextChars = 30000
    expect(store.contextPercent).toBe(50)
  })

  it('clamps context percent at 100', () => {
    const store = useCodingStore()
    store.contextChars = 99999
    expect(store.contextPercent).toBe(100)
  })

  it('appends tool activity on tool_call event', () => {
    const store = useCodingStore()
    store.messages = [{ role: 'assistant', content: '', tools: [], isThinking: true }]
    store.handleServerEvent({
      type: 'tool_call',
      tool: 'read_file',
      args: { path: 'README.md' },
    } as never)
    expect(store.messages[0].tools).toHaveLength(1)
    expect(store.messages[0].tools![0].tool).toBe('read_file')
    expect(store.messages[0].tools![0].status).toBe('running')
  })

  it('updates tool activity on tool_result event', () => {
    const store = useCodingStore()
    store.messages = [
      {
        role: 'assistant',
        content: '',
        tools: [{ tool: 'read_file', args: {}, status: 'running', content: '' }],
        isThinking: true,
      },
    ]
    store.handleServerEvent({
      type: 'tool_result',
      tool: 'read_file',
      args: {},
      content: '# Sage',
      is_error: false,
    } as never)
    expect(store.messages[0].tools![0].status).toBe('done')
    expect(store.messages[0].tools![0].content).toBe('# Sage')
  })

  it('stores pending approval from approval_required event', () => {
    const store = useCodingStore()
    store.sessionId = 'c1'
    store.handleServerEvent({
      type: 'approval_required',
      approval_id: 'appr_1',
      tool: 'write_file',
      args: { path: 'README.md' },
      description: 'write_file requires approval.',
      pattern_key: 'tool:write_file',
    } as never)

    expect(store.pendingApproval?.approval_id).toBe('appr_1')
    expect(store.pendingApproval?.tool).toBe('write_file')
    store.disconnect()
  })

  it('builds write approval diff preview from current file content', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ path: 'README.md', content: 'old title\n', lines: 1 }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const store = useCodingStore()
    store.sessionId = 'c1'

    store.handleServerEvent({
      type: 'approval_required',
      approval_id: 'appr_1',
      tool: 'write_file',
      args: { path: 'README.md', content: 'new title\n' },
      description: 'write_file requires approval.',
      pattern_key: 'tool:write_file',
    } as never)
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(store.pendingApproval?.diff_preview).toEqual([
      { type: 'remove', text: 'old title' },
      { type: 'add', text: 'new title' },
    ])
    store.disconnect()
  })

  it('responds to pending approval and clears it', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true })
    vi.stubGlobal('fetch', fetchMock)
    const store = useCodingStore()
    store.sessionId = 'c1'
    store.pendingApproval = {
      approval_id: 'appr_1',
      session_id: 'c1',
      tool: 'write_file',
      args: {},
      description: 'write_file requires approval.',
      pattern_key: 'tool:write_file',
    }

    await store.respondApproval('session')

    expect(fetchMock).toHaveBeenCalled()
    expect(store.pendingApproval).toBeNull()
  })

  it('caches file tree directories', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ path: '.', entries: [{ name: 'src', is_dir: true }] }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const store = useCodingStore()
    store.sessionId = 'c1'

    await store.loadFiles('.')
    await store.loadFiles('.')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(store.fileTreeEntries).toEqual([{ name: 'src', is_dir: true }])
    expect(store.expandedDirs.has('.')).toBe(true)
  })

  it('refreshes workspace view after successful write tools', async () => {
    const fetchMock = vi.fn().mockImplementation((url: URL) => {
      if (url.pathname.endsWith('/git/status')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            is_git: true,
            branch: 'main',
            dirty_count: 1,
            changed_files: ['note.txt'],
          }),
        })
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ path: '.', entries: [{ name: 'note.txt', is_dir: false }] }),
      })
    })
    vi.stubGlobal('fetch', fetchMock)
    const store = useCodingStore()
    store.sessionId = 'c1'
    store.messages = [
      {
        role: 'assistant',
        content: '',
        tools: [{ tool: 'write_file', args: {}, status: 'running', content: '' }],
        isThinking: true,
      },
    ]

    store.handleServerEvent({
      type: 'tool_result',
      tool: 'write_file',
      args: {},
      content: 'wrote note.txt',
      is_error: false,
    } as never)
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(store.gitStatus.dirty_count).toBe(1)
    expect(store.fileTreeEntries).toEqual([{ name: 'note.txt', is_dir: false }])
  })

  it('finalizes message on final event', () => {
    const store = useCodingStore()
    store.messages = [{ role: 'assistant', content: '', tools: [], isThinking: true }]
    store.isThinking = true
    store.handleServerEvent({ type: 'final', content: '完成' } as never)
    expect(store.messages[0].content).toBe('完成')
    expect(store.messages[0].isThinking).toBe(false)
    expect(store.isThinking).toBe(false)
  })

  it('handles cancelled event as a stopped assistant message', () => {
    const store = useCodingStore()
    store.messages = [{ role: 'assistant', content: '', tools: [], isThinking: true }]
    store.isThinking = true

    store.handleServerEvent({ type: 'cancelled', content: '已停止当前运行。' } as never)

    expect(store.messages[0].content).toBe('已停止当前运行。')
    expect(store.messages[0].isThinking).toBe(false)
    expect(store.isThinking).toBe(false)
  })

  it('requests stop for current run', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true })
    vi.stubGlobal('fetch', fetchMock)
    const store = useCodingStore()
    store.sessionId = 'c1'
    store.isThinking = true

    await store.stopCurrentRun()

    expect(fetchMock).toHaveBeenCalledWith(expect.any(URL), { method: 'POST' })
  })
})
