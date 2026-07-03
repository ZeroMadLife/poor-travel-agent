import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getSessionMessages, listSessions } from '../api/chat'
import type { HistoryMessage, SessionSummary } from '../types/api'

export const useSessionStore = defineStore('session', () => {
  const sessions = ref<SessionSummary[]>([])
  const messages = ref<HistoryMessage[]>([])
  const activeSessionId = ref('')
  const isLoading = ref(false)
  const error = ref('')

  async function loadSessions(userId: string) {
    if (!userId) return
    isLoading.value = true
    error.value = ''
    try {
      const response = await listSessions(userId)
      sessions.value = response.sessions
    } catch (err) {
      error.value = err instanceof Error ? err.message : '历史会话加载失败'
    } finally {
      isLoading.value = false
    }
  }

  async function selectSession(sessionId: string) {
    activeSessionId.value = sessionId
    isLoading.value = true
    error.value = ''
    try {
      const response = await getSessionMessages(sessionId)
      messages.value = response.messages
    } catch (err) {
      error.value = err instanceof Error ? err.message : '会话消息加载失败'
    } finally {
      isLoading.value = false
    }
  }

  function clearSelection() {
    activeSessionId.value = ''
    messages.value = []
  }

  return {
    sessions,
    messages,
    activeSessionId,
    isLoading,
    error,
    loadSessions,
    selectSession,
    clearSelection,
  }
})
