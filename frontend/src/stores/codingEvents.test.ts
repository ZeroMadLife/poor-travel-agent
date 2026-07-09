import { describe, expect, it } from 'vitest'
import { ref } from 'vue'
import { applyCodingEvent, type ChatMessage } from './codingEvents'
import type { CodingApproval } from '../types/api'

function state() {
  return {
    sessionId: ref('coding_1'),
    messages: ref<ChatMessage[]>([]),
    isThinking: ref(false),
    errorMessage: ref(''),
    contextChars: ref(0),
    pendingApproval: ref<CodingApproval | null>(null),
  }
}

describe('codingEvents', () => {
  it('appends tool activity on tool_call', () => {
    const current = state()
    current.messages.value = [{ role: 'assistant', content: '', tools: [], isThinking: true }]

    applyCodingEvent(current, {
      type: 'tool_call',
      tool: 'read_file',
      args: { path: 'README.md' },
    })

    expect(current.messages.value[0].tools).toHaveLength(1)
    expect(current.messages.value[0].tools![0].status).toBe('running')
  })

  it('updates the latest running tool on tool_result', () => {
    const current = state()
    current.messages.value = [
      {
        role: 'assistant',
        content: '',
        tools: [{ tool: 'read_file', args: {}, status: 'running', content: '' }],
        isThinking: true,
      },
    ]

    const effect = applyCodingEvent(current, {
      type: 'tool_result',
      tool: 'read_file',
      args: {},
      content: '# Sage',
      is_error: false,
    })

    expect(effect.toolResult?.tool).toBe('read_file')
    expect(current.messages.value[0].tools![0].status).toBe('done')
    expect(current.messages.value[0].tools![0].content).toBe('# Sage')
  })

  it('finalizes assistant thinking message on terminal events', () => {
    const current = state()
    current.messages.value = [{ role: 'assistant', content: '', tools: [], isThinking: true }]
    current.isThinking.value = true

    const effect = applyCodingEvent(current, { type: 'final', content: '完成' })

    expect(effect.terminal).toBe(true)
    expect(current.messages.value[0].content).toBe('完成')
    expect(current.messages.value[0].isThinking).toBe(false)
    expect(current.isThinking.value).toBe(false)
  })

  it('sets pending approval from approval_required', () => {
    const current = state()

    const effect = applyCodingEvent(current, {
      type: 'approval_required',
      approval_id: 'appr_1',
      tool: 'write_file',
      args: { path: 'README.md' },
      description: 'write_file requires approval.',
      pattern_key: 'tool:write_file',
    })

    expect(effect.approvalRequired).toBe(true)
    expect(current.pendingApproval.value?.approval_id).toBe('appr_1')
    expect(current.pendingApproval.value?.session_id).toBe('coding_1')
  })
})
