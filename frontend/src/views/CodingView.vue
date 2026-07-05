<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import ToolCallTrace from '../components/ToolCallTrace.vue'
import { buildCodingStreamUrl, startCodingSession } from '../api/coding'
import type { CodingServerEvent, ToolCallStatus } from '../types/api'

type Message = {
  role: 'user' | 'assistant'
  content: string
}

const sessionId = ref('')
const workspaceRoot = ref('')
const input = ref('')
const messages = ref<Message[]>([])
const toolCalls = ref<ToolCallStatus[]>([])
const isThinking = ref(false)
const errorMessage = ref('')
const socket = ref<WebSocket | null>(null)
const messagesRef = ref<HTMLElement | null>(null)

const canSend = computed(() => Boolean(input.value.trim()) && Boolean(sessionId.value) && !isThinking.value)

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

async function ensureSession() {
  if (sessionId.value) return
  const session = await startCodingSession()
  sessionId.value = session.session_id
  workspaceRoot.value = session.workspace_root
}

function connectSocket() {
  if (!sessionId.value) return
  socket.value?.close()
  const ws = new WebSocket(buildCodingStreamUrl(sessionId.value))
  ws.onmessage = (event) => handleServerEvent(JSON.parse(event.data) as CodingServerEvent)
  ws.onerror = () => {
    errorMessage.value = '连接中断'
    isThinking.value = false
  }
  socket.value = ws
}

async function initialize() {
  try {
    await ensureSession()
    connectSocket()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  }
}

function handleServerEvent(event: CodingServerEvent) {
  if (event.type === 'tool_call') {
    toolCalls.value.push({
      tool: event.tool,
      args: event.args,
      status: 'running',
      message: `正在执行 ${event.tool}`,
    })
    return
  }

  if (event.type === 'tool_result') {
    const target = [...toolCalls.value].reverse().find((call) => call.tool === event.tool && call.status === 'running')
    if (target) {
      target.status = event.is_error ? 'error' : 'done'
      target.message = event.content.slice(0, 160)
    } else {
      toolCalls.value.push({
        tool: event.tool,
        args: event.args,
        status: event.is_error ? 'error' : 'done',
        message: event.content.slice(0, 160),
      })
    }
    return
  }

  if (event.type === 'final' || event.type === 'step_limit') {
    messages.value.push({ role: 'assistant', content: event.content })
    isThinking.value = false
    scrollToBottom()
    return
  }

  if (event.type === 'error') {
    errorMessage.value = event.message
    isThinking.value = false
  }
}

function sendMessage() {
  const content = input.value.trim()
  if (!content || !socket.value || socket.value.readyState !== WebSocket.OPEN) return
  messages.value.push({ role: 'user', content })
  input.value = ''
  errorMessage.value = ''
  toolCalls.value = []
  isThinking.value = true
  socket.value.send(JSON.stringify({ content }))
  scrollToBottom()
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

onMounted(initialize)
onBeforeUnmount(() => socket.value?.close())
</script>

<template>
  <main class="coding-view">
    <header class="coding-header">
      <div>
        <h1>CodeAssist</h1>
        <p>{{ workspaceRoot || '...' }}</p>
      </div>
      <span class="session-pill">{{ sessionId ? '已连接' : '连接中' }}</span>
    </header>

    <section ref="messagesRef" class="coding-messages">
      <article v-for="(message, index) in messages" :key="index" :class="['message', message.role]">
        <pre>{{ message.content }}</pre>
      </article>
      <ToolCallTrace :is-thinking="isThinking" :tool-calls="toolCalls" />
      <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
    </section>

    <footer class="coding-composer">
      <textarea
        v-model="input"
        rows="2"
        :disabled="!sessionId || isThinking"
        placeholder="读 README.md 告诉我项目叫什么"
        @keydown="onKeydown"
      />
      <button :disabled="!canSend" @click="sendMessage">
        {{ isThinking ? '执行中' : '发送' }}
      </button>
    </footer>
  </main>
</template>

<style scoped>
.coding-view {
  display: grid;
  grid-template-rows: auto 1fr auto;
  min-height: calc(100vh - 56px);
  background: #f7f8fa;
  color: #111827;
}

.coding-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
  background: #ffffff;
}

.coding-header h1 {
  margin: 0;
  font-size: 20px;
}

.coding-header p {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.session-pill {
  padding: 4px 10px;
  border: 1px solid #d1d5db;
  border-radius: 999px;
  color: #374151;
  background: #f9fafb;
  font-size: 13px;
}

.coding-messages {
  min-height: 0;
  overflow-y: auto;
  padding: 20px;
}

.message {
  max-width: 860px;
  margin: 0 0 12px;
  padding: 12px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
}

.message.user {
  margin-left: auto;
  background: #eef6ff;
}

pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
}

.error-text {
  color: #b91c1c;
}

.coding-composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  padding: 14px 20px;
  border-top: 1px solid #e5e7eb;
  background: #ffffff;
}

.coding-composer textarea {
  width: 100%;
  resize: vertical;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 10px 12px;
  line-height: 1.5;
}

.coding-composer button {
  min-width: 84px;
  border: 0;
  border-radius: 8px;
  background: #111827;
  color: #ffffff;
  font-weight: 700;
}

.coding-composer button:disabled {
  background: #9ca3af;
}

@media (max-width: 720px) {
  .coding-composer {
    grid-template-columns: 1fr;
  }
}
</style>
