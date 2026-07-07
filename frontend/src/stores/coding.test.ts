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

  it('finalizes message on final event', () => {
    const store = useCodingStore()
    store.messages = [{ role: 'assistant', content: '', tools: [], isThinking: true }]
    store.isThinking = true
    store.handleServerEvent({ type: 'final', content: '完成' } as never)
    expect(store.messages[0].content).toBe('完成')
    expect(store.messages[0].isThinking).toBe(false)
    expect(store.isThinking).toBe(false)
  })
})
