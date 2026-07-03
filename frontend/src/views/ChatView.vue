<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import ChatInput from '../components/ChatInput.vue'
import MessageBubble from '../components/MessageBubble.vue'
import { useChatStore } from '../stores/chat'
import { useAuth } from '../composables/useAuth'
import type { Itinerary, ToolCallStatus } from '../types/api'

const chatStore = useChatStore()
const auth = useAuth()
const messagesContainer = ref<HTMLElement | null>(null)
const isAuthenticated = ref(auth.isAuthenticated())
const passphrase = ref(auth.storedPassphrase ?? '')
const authError = ref(false)

interface UIMessage {
  role: 'user' | 'assistant'
  content: string
  isThinking?: boolean
  statusMessage?: string
  toolCalls?: ToolCallStatus[]
  itinerary?: Itinerary | null
}

const messages = ref<UIMessage[]>([])

function lastAssistantMessage() {
  return [...messages.value].reverse().find((m) => m.role === 'assistant')
}

// 进度事件 → 显示“正在思考中/正在查询”等状态
watch(
  () => chatStore.events,
  (events) => {
    const latest = events.at(-1)
    const last = lastAssistantMessage()
    if (latest && last) {
      last.isThinking = true
      last.statusMessage = latest.message || '正在思考中...'
    }
  },
  { deep: true },
)

// 工具调用事件 → 更新当前 assistant 消息
watch(
  () => chatStore.toolCalls,
  (calls) => {
    const last = lastAssistantMessage()
    if (last) {
      last.toolCalls = calls.map((c) => ({
        tool: c.tool,
        args: c.args,
        status: c.status,
        message: c.message,
      }))
    }
  },
  { deep: true },
)

// 结果事件 → 更新当前 assistant 消息
watch(
  () => chatStore.result,
  (result) => {
    if (!result) return
    const last = lastAssistantMessage()
    if (last) {
      last.content = result.content
      last.itinerary = result.itinerary
      last.isThinking = false
      last.statusMessage = undefined
    }
  },
)

// 错误事件 → 不让 assistant 气泡一直空着
watch(
  () => chatStore.errors,
  (errors) => {
    const latest = errors.at(-1)
    const last = lastAssistantMessage()
    if (latest && last) {
      last.content = `请求失败：${latest.message}`
      last.isThinking = false
      last.statusMessage = undefined
    }
  },
  { deep: true },
)

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

async function handleSend(content: string) {
  messages.value.push({ role: 'user', content })
  messages.value.push({
    role: 'assistant',
    content: '',
    isThinking: true,
    statusMessage: '正在思考中...',
  })
  scrollToBottom()

  await chatStore.sendMessage(content, auth.getUserId() || 'anonymous')
  scrollToBottom()
}

async function handleAuth() {
  const valid = await auth.verify(passphrase.value.trim())
  authError.value = !valid
  isAuthenticated.value = valid
}
</script>

<template>
  <div v-if="!isAuthenticated" class="auth-screen">
    <h1>🧳 TourSwarm 穷游助手</h1>
    <p>请输入口令进入</p>
    <input
      v-model="passphrase"
      type="password"
      placeholder="口令"
      @keyup.enter="handleAuth"
    />
    <button @click="handleAuth">进入</button>
    <p v-if="authError" class="error">口令错误</p>
  </div>
  <div v-else class="chat-view">
    <header class="chat-header">
      <h1>🧳 TourSwarm 穷游助手</h1>
    </header>
    <div class="messages" ref="messagesContainer">
      <div class="welcome" v-if="messages.length === 0">
        <p>👋 你好！我是你的个人穷游助手。</p>
        <p>试试问我：</p>
        <ul>
          <li>"帮我规划杭州2日游500元"</li>
          <li>"附近有什么好吃的"</li>
          <li>"杭州明天天气怎么样"</li>
        </ul>
      </div>
      <MessageBubble
        v-for="(msg, i) in messages"
        :key="i"
        :role="msg.role"
        :content="msg.content"
        :is-thinking="msg.isThinking"
        :status-message="msg.statusMessage"
        :tool-calls="msg.toolCalls"
        :itinerary="msg.itinerary"
      />
    </div>
    <ChatInput :disabled="chatStore.isExecuting" @submit="handleSend" />
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 800px;
  margin: 0 auto;
}
.chat-header {
  padding: 1rem;
  border-bottom: 1px solid #e5e7eb;
}
.chat-header h1 {
  font-size: 1.25rem;
  margin: 0;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}
.welcome {
  color: #6b7280;
  padding: 2rem;
  text-align: center;
}
.welcome ul {
  list-style: none;
  padding: 0;
}
.welcome li {
  padding: 0.25rem 0;
}
.auth-screen {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  justify-content: center;
  max-width: 360px;
  height: 100vh;
  margin: 0 auto;
  padding: 1rem;
  text-align: center;
}
.auth-screen input {
  padding: 0.65rem 0.8rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 1rem;
}
.auth-screen button {
  padding: 0.65rem 0.8rem;
  border: none;
  border-radius: 8px;
  color: white;
  background: #2563eb;
  cursor: pointer;
  font-size: 1rem;
}
.error {
  color: #dc2626;
}
</style>
