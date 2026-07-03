<script setup lang="ts">
import type { SessionSummary } from '../types/api'

defineProps<{
  sessions: SessionSummary[]
  activeSessionId: string
}>()

const emit = defineEmits<{
  select: [sessionId: string]
  new: []
}>()
</script>

<template>
  <aside class="session-list">
    <div class="session-header">
      <h2>历史会话</h2>
      <button class="new-session" @click="emit('new')">+ 新对话</button>
    </div>
    <div v-if="sessions.length === 0" class="empty">暂无历史</div>
    <button
      v-for="session in sessions"
      :key="session.session_id"
      class="session-item"
      :class="{ active: session.session_id === activeSessionId }"
      @click="emit('select', session.session_id)"
    >
      <span>{{ session.title || '未命名会话' }}</span>
      <small>{{ new Date(session.updated_at).toLocaleDateString() }}</small>
    </button>
  </aside>
</template>

<style scoped>
.session-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 240px;
  min-width: 220px;
  padding: 1rem;
  border-right: 1px solid #e5e7eb;
  background: #ffffff;
}

.session-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.session-header h2 {
  margin: 0;
  font-size: 1rem;
}

.new-session,
.session-item {
  border: 0;
  border-radius: 8px;
  cursor: pointer;
  font: inherit;
}

.new-session {
  padding: 0.35rem 0.55rem;
  color: #ffffff;
  background: #2563eb;
  white-space: nowrap;
}

.session-item {
  display: grid;
  gap: 0.2rem;
  width: 100%;
  padding: 0.65rem;
  color: #374151;
  background: #f9fafb;
  text-align: left;
}

.session-item.active {
  color: #1d4ed8;
  background: #dbeafe;
}

.session-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-item small,
.empty {
  color: #6b7280;
  font-size: 0.8rem;
}
</style>
