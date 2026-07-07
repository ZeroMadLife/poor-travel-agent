import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  buildCodingStreamUrl,
  fetchCodingFile,
  fetchCodingFiles,
  fetchCodingGitStatus,
  fetchCodingMcpServers,
  fetchCodingModels,
  fetchCodingSkills,
  startCodingSession,
  switchCodingModel,
} from '../api/coding'
import type {
  CodingFileEntry,
  CodingGitStatusResponse,
  CodingMcpServer,
  CodingModel,
  CodingServerEvent,
  CodingSkillSummary,
  CodingToolCallEvent,
  CodingToolResultEvent,
} from '../types/api'

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

export const useCodingStore = defineStore('coding', () => {
  const sessionId = ref('')
  const workspaceRoot = ref('')
  const messages = ref<ChatMessage[]>([])
  const isThinking = ref(false)
  const errorMessage = ref('')
  const currentModelId = ref('')
  const contextChars = ref(0)
  const contextBudget = 60000

  const skills = ref<CodingSkillSummary[]>([])
  const mcpServers = ref<CodingMcpServer[]>([])
  const models = ref<CodingModel[]>([])
  const gitStatus = ref<CodingGitStatusResponse>({
    is_git: false,
    branch: '',
    dirty_count: 0,
    changed_files: [],
  })

  const fileTreePath = ref('.')
  const fileTreeEntries = ref<CodingFileEntry[]>([])
  const previewPath = ref('')
  const previewContent = ref('')
  const breadcrumb = computed(() => fileTreePath.value.split('/').filter(Boolean))

  let socket: WebSocket | null = null

  const contextPercent = computed(() =>
    Math.min(100, Math.round((contextChars.value / contextBudget) * 100)),
  )

  async function initialize() {
    if (sessionId.value) return
    const session = await startCodingSession()
    sessionId.value = session.session_id
    workspaceRoot.value = session.workspace_root
    await Promise.all([
      loadSkills(),
      loadMcpServers(),
      loadModels(),
      loadGitStatus(),
      loadFiles('.'),
    ])
    connectSocket()
  }

  function connectSocket() {
    if (!sessionId.value) return
    socket?.close()
    socket = new WebSocket(buildCodingStreamUrl(sessionId.value))
    socket.onmessage = (event) => {
      handleServerEvent(JSON.parse(event.data) as CodingServerEvent)
    }
    socket.onerror = () => {
      errorMessage.value = '连接中断'
      isThinking.value = false
    }
  }

  function handleServerEvent(event: CodingServerEvent) {
    if (event.type === 'model_requested') {
      if (event.prompt_chars) contextChars.value = event.prompt_chars
      return
    }
    if (event.type === 'tool_call') {
      appendToolActivity(event as CodingToolCallEvent)
      return
    }
    if (event.type === 'tool_result') {
      updateToolActivity(event as CodingToolResultEvent)
      return
    }
    if (event.type === 'final' || event.type === 'step_limit') {
      finalizeCurrentMessage(event.content)
      isThinking.value = false
      return
    }
    if (event.type === 'error') {
      errorMessage.value = event.message
      isThinking.value = false
    }
  }

  function appendToolActivity(event: CodingToolCallEvent) {
    const lastMessage = messages.value[messages.value.length - 1]
    if (!lastMessage || lastMessage.role !== 'assistant' || !lastMessage.isThinking) {
      messages.value.push({
        role: 'assistant',
        content: '',
        tools: [],
        isThinking: true,
      })
    }
    const current = messages.value[messages.value.length - 1]
    current.tools = current.tools || []
    current.tools.push({
      tool: event.tool,
      args: event.args,
      status: 'running',
      content: '',
    })
  }

  function updateToolActivity(event: CodingToolResultEvent) {
    for (const msg of [...messages.value].reverse()) {
      if (!msg.tools) continue
      const target = [...msg.tools].reverse().find(
        (t) => t.tool === event.tool && t.status === 'running',
      )
      if (target) {
        target.status = event.is_error ? 'error' : 'done'
        target.content = event.content.slice(0, 2000)
        return
      }
    }
  }

  function finalizeCurrentMessage(content: string) {
    const lastMessage = messages.value[messages.value.length - 1]
    if (lastMessage && lastMessage.isThinking) {
      lastMessage.content = content
      lastMessage.isThinking = false
    } else {
      messages.value.push({ role: 'assistant', content })
    }
  }

  function sendMessage(content: string) {
    if (!content.trim() || !socket || socket.readyState !== WebSocket.OPEN) return
    messages.value.push({ role: 'user', content })
    isThinking.value = true
    errorMessage.value = ''
    socket.send(JSON.stringify({ content }))
  }

  async function loadSkills() {
    try {
      const res = await fetchCodingSkills()
      skills.value = res.skills
    } catch {
      skills.value = []
    }
  }

  async function loadMcpServers() {
    try {
      const res = await fetchCodingMcpServers()
      mcpServers.value = res.servers
    } catch {
      mcpServers.value = []
    }
  }

  async function loadModels() {
    try {
      const res = await fetchCodingModels()
      models.value = res.models
      if (res.current) currentModelId.value = res.current
      else if (res.models.length > 0) currentModelId.value = res.models[0].id
    } catch {
      models.value = []
    }
  }

  async function loadGitStatus() {
    if (!sessionId.value) return
    try {
      gitStatus.value = await fetchCodingGitStatus(sessionId.value)
    } catch {
      gitStatus.value = { is_git: false, branch: '', dirty_count: 0, changed_files: [] }
    }
  }

  async function loadFiles(path: string) {
    if (!sessionId.value) return
    try {
      const res = await fetchCodingFiles(sessionId.value, path)
      fileTreePath.value = path
      fileTreeEntries.value = res.entries
    } catch {
      fileTreeEntries.value = []
    }
  }

  async function loadFilePreview(path: string) {
    if (!sessionId.value) return
    try {
      const res = await fetchCodingFile(sessionId.value, path)
      previewPath.value = path
      previewContent.value = res.content
    } catch {
      previewPath.value = path
      previewContent.value = '无法加载文件'
    }
  }

  async function changeModel(modelId: string) {
    if (!sessionId.value) return
    await switchCodingModel(sessionId.value, modelId)
    currentModelId.value = modelId
  }

  function disconnect() {
    socket?.close()
    socket = null
  }

  return {
    sessionId,
    workspaceRoot,
    messages,
    isThinking,
    errorMessage,
    currentModelId,
    contextChars,
    contextBudget,
    contextPercent,
    skills,
    mcpServers,
    models,
    gitStatus,
    fileTreePath,
    fileTreeEntries,
    previewPath,
    previewContent,
    breadcrumb,
    initialize,
    sendMessage,
    handleServerEvent,
    loadSkills,
    loadMcpServers,
    loadModels,
    loadGitStatus,
    loadFiles,
    loadFilePreview,
    changeModel,
    disconnect,
  }
})
