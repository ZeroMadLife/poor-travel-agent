<script setup lang="ts">
import { computed } from 'vue'
import type { Itinerary } from '../types/api'
import ItineraryCard from './ItineraryCard.vue'
import ToolCallTrace from './ToolCallTrace.vue'
import { useMarkdown } from '../composables/useMarkdown'

const props = defineProps<{
  role: 'user' | 'assistant'
  content: string
  isThinking?: boolean
  statusMessage?: string
  toolCalls?: Array<{
    tool: string
    args: Record<string, unknown>
    status: 'running' | 'done' | 'error'
    message?: string
  }>
  itinerary?: Itinerary | null
}>()

const { render } = useMarkdown()
const renderedContent = computed(() => {
  if (!props.content) return ''
  // assistant 消息渲染 Markdown，user 消息保持纯文本
  if (props.role === 'assistant') {
    return render(props.content)
  }
  // user 消息转义 HTML 后保留换行
  return props.content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
})
</script>

<template>
  <div class="message" :class="role">
    <div class="avatar">{{ role === 'user' ? '👤' : '🤖' }}</div>
    <div class="bubble">
      <ToolCallTrace
        v-if="toolCalls && toolCalls.length > 0"
        :is-thinking="isThinking"
        :tool-calls="toolCalls"
      />
      <div v-if="role === 'assistant' && isThinking" class="thinking">
        <span class="thinking-dot" />
        <span>{{ statusMessage || '正在思考中...' }}</span>
      </div>
      <div v-if="content" class="content markdown-body" v-html="renderedContent" />
      <ItineraryCard v-if="itinerary" :itinerary="itinerary" />
    </div>
  </div>
</template>

<style scoped>
.message {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.message.user {
  flex-direction: row-reverse;
}
.avatar {
  font-size: 1.5rem;
  flex-shrink: 0;
}
.bubble {
  max-width: 70%;
  padding: 0.75rem 1rem;
  border-radius: 12px;
  background: #f9fafb;
}
.message.user .bubble {
  background: #dbeafe;
}
.content {
  margin: 0.5rem 0;
  line-height: 1.6;
  font-size: 0.95rem;
  word-break: break-word;
}
.thinking {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #6b7280;
  font-size: 0.95rem;
  line-height: 1.5;
}
.thinking-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 999px;
  background: #2563eb;
  animation: thinking-pulse 1.1s ease-in-out infinite;
}
@keyframes thinking-pulse {
  0%,
  100% {
    opacity: 0.35;
    transform: scale(0.8);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}

/* Markdown 内容样式 */
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 0.75rem 0 0.4rem;
  font-weight: 600;
  line-height: 1.3;
}
.markdown-body :deep(h1) { font-size: 1.3rem; }
.markdown-body :deep(h2) { font-size: 1.15rem; }
.markdown-body :deep(h3) { font-size: 1.05rem; }
.markdown-body :deep(h4) { font-size: 1rem; }
.markdown-body :deep(p) {
  margin: 0.4rem 0;
}
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 0.4rem 0;
  padding-left: 1.5rem;
}
.markdown-body :deep(li) {
  margin: 0.2rem 0;
}
.markdown-body :deep(strong) {
  font-weight: 600;
}
.markdown-body :deep(em) {
  font-style: italic;
}
.markdown-body :deep(a) {
  color: #2563eb;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.markdown-body :deep(a:hover) {
  color: #1d4ed8;
}
.markdown-body :deep(blockquote) {
  margin: 0.5rem 0;
  padding: 0.5rem 0.75rem;
  border-left: 3px solid #d1d5db;
  background: #f3f4f6;
  border-radius: 0 4px 4px 0;
  color: #4b5563;
}
.markdown-body :deep(code) {
  padding: 0.15rem 0.35rem;
  background: #f3f4f6;
  border-radius: 4px;
  font-size: 0.875em;
  font-family: ui-monospace, monospace;
}
.markdown-body :deep(pre) {
  margin: 0.5rem 0;
  padding: 0.75rem;
  background: #1f2937;
  border-radius: 8px;
  overflow-x: auto;
}
.markdown-body :deep(pre code) {
  padding: 0;
  background: none;
  color: #e5e7eb;
}
.markdown-body :deep(table) {
  border-collapse: collapse;
  margin: 0.5rem 0;
  font-size: 0.875rem;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #e5e7eb;
  padding: 0.4rem 0.6rem;
  text-align: left;
}
.markdown-body :deep(th) {
  background: #f9fafb;
  font-weight: 600;
}
.markdown-body :deep(hr) {
  border: 0;
  border-top: 1px solid #e5e7eb;
  margin: 0.75rem 0;
}
</style>
