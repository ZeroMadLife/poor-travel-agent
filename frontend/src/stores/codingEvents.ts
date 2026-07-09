import type {
  CodingApproval,
  CodingApprovalRequiredEvent,
  CodingServerEvent,
  CodingToolCallEvent,
  CodingToolResultEvent,
} from '../types/api'
import type { Ref } from 'vue'

export type ToolActivity = {
  tool: string
  args: Record<string, unknown>
  status: 'running' | 'done' | 'error'
  content: string
  durationMs?: number
}

export type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
  tools?: ToolActivity[]
  isThinking?: boolean
}

export type CodingEventState = {
  sessionId: Ref<string>
  messages: Ref<ChatMessage[]>
  isThinking: Ref<boolean>
  errorMessage: Ref<string>
  contextChars: Ref<number>
  pendingApproval: Ref<CodingApproval | null>
}

export type CodingEventEffect = {
  approvalRequired?: boolean
  terminal?: boolean
  toolResult?: CodingToolResultEvent
}

export function applyCodingEvent(
  state: CodingEventState,
  event: CodingServerEvent,
): CodingEventEffect {
  if (event.type === 'model_requested') {
    if (event.prompt_chars) state.contextChars.value = event.prompt_chars
    return {}
  }
  if (event.type === 'tool_call') {
    appendToolActivity(state.messages.value, event)
    return {}
  }
  if (event.type === 'approval_required') {
    state.pendingApproval.value = approvalFromEvent(state.sessionId.value, event)
    return { approvalRequired: true }
  }
  if (event.type === 'tool_result') {
    updateToolActivity(state.messages.value, event)
    return { toolResult: event }
  }
  if (event.type === 'final' || event.type === 'step_limit' || event.type === 'cancelled') {
    finalizeCurrentMessage(state.messages.value, event.content)
    state.isThinking.value = false
    return { terminal: true }
  }
  if (event.type === 'error') {
    state.errorMessage.value = event.message
    state.isThinking.value = false
    return { terminal: true }
  }
  return {}
}

function approvalFromEvent(sessionId: string, event: CodingApprovalRequiredEvent): CodingApproval {
  return {
    approval_id: event.approval_id,
    session_id: sessionId,
    tool: event.tool,
    args: event.args,
    description: event.description,
    pattern_key: event.pattern_key,
  }
}

function appendToolActivity(messages: ChatMessage[], event: CodingToolCallEvent) {
  const lastMessage = messages[messages.length - 1]
  if (!lastMessage || lastMessage.role !== 'assistant' || !lastMessage.isThinking) {
    messages.push({
      role: 'assistant',
      content: '',
      tools: [],
      isThinking: true,
    })
  }
  const current = messages[messages.length - 1]
  current.tools = current.tools || []
  current.tools.push({
    tool: event.tool,
    args: event.args,
    status: 'running',
    content: '',
  })
}

function updateToolActivity(messages: ChatMessage[], event: CodingToolResultEvent) {
  for (const msg of [...messages].reverse()) {
    if (!msg.tools) continue
    const target = [...msg.tools].reverse().find(
      (tool) => tool.tool === event.tool && tool.status === 'running',
    )
    if (target) {
      target.status = event.is_error ? 'error' : 'done'
      target.content = event.content.slice(0, 2000)
      return
    }
  }
}

function finalizeCurrentMessage(messages: ChatMessage[], content: string) {
  const lastMessage = messages[messages.length - 1]
  if (lastMessage && lastMessage.isThinking) {
    lastMessage.content = content
    lastMessage.isThinking = false
  } else {
    messages.push({ role: 'assistant', content })
  }
}
