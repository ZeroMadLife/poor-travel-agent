import { defineStore } from 'pinia'
import { ref } from 'vue'
import { buildChatStreamUrl, startChat } from '../api/chat'
import type { ErrorEvent, ProgressEvent, ResultEvent, ServerEvent, ToolCallEvent } from '../types/api'

export type ConnectionStatus = 'idle' | 'connecting' | 'connected' | 'closed' | 'error'
export type SocketFactory = (url: string) => WebSocket

export const useChatStore = defineStore('chat', () => {
  const events = ref<ProgressEvent[]>([])
  const toolCalls = ref<ToolCallEvent[]>([])
  const errors = ref<ErrorEvent[]>([])
  const result = ref<ResultEvent | null>(null)
  const currentSessionId = ref('')
  const connectionStatus = ref<ConnectionStatus>('idle')
  let activeSocket: WebSocket | null = null

  function resetStreamState() {
    events.value = []
    toolCalls.value = []
    errors.value = []
    result.value = null
  }

  function handleServerEvent(event: ServerEvent) {
    if (event.type === 'progress') {
      events.value.push(event)
      return
    }
    if (event.type === 'tool_call') {
      toolCalls.value.push(event)
      return
    }
    if (event.type === 'result') {
      result.value = event
      return
    }
    errors.value.push(event)
    connectionStatus.value = 'error'
  }

  function closeStream() {
    activeSocket?.close()
    activeSocket = null
  }

  function connectStream(
    sessionId: string,
    socketFactory: SocketFactory = (url: string) => new WebSocket(url),
  ) {
    closeStream()
    currentSessionId.value = sessionId
    connectionStatus.value = 'connecting'
    const socket = socketFactory(buildChatStreamUrl(sessionId))
    activeSocket = socket

    socket.onopen = () => {
      connectionStatus.value = 'connected'
    }
    socket.onmessage = (message: MessageEvent) => {
      handleServerEvent(JSON.parse(String(message.data)) as ServerEvent)
    }
    socket.onerror = () => {
      errors.value.push({ type: 'error', message: 'WebSocket connection failed', recoverable: true })
      connectionStatus.value = 'error'
    }
    socket.onclose = () => {
      if (connectionStatus.value !== 'error') {
        connectionStatus.value = 'closed'
      }
    }
  }

  async function startPlanning(content: string, userId = 'anonymous') {
    resetStreamState()
    const response = await startChat(content, userId)
    connectStream(response.session_id)
  }

  return {
    events,
    toolCalls,
    errors,
    result,
    currentSessionId,
    connectionStatus,
    connectStream,
    closeStream,
    startPlanning,
  }
})
