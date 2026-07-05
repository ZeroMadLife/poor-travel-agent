<script setup lang="ts">
import { Code2, Map } from 'lucide-vue-next'
import { ref } from 'vue'
import ChatView from './views/ChatView.vue'
import CodingView from './views/CodingView.vue'

const activeView = ref<'travel' | 'coding'>('travel')
</script>

<template>
  <div class="app-shell">
    <nav class="app-nav">
      <button :class="{ active: activeView === 'travel' }" @click="activeView = 'travel'">
        <Map :size="17" />
        <span>旅行</span>
      </button>
      <button :class="{ active: activeView === 'coding' }" @click="activeView = 'coding'">
        <Code2 :size="17" />
        <span>代码</span>
      </button>
    </nav>
    <ChatView v-if="activeView === 'travel'" />
    <CodingView v-else />
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.app-nav {
  display: flex;
  gap: 6px;
  align-items: center;
  height: 56px;
  padding: 8px 14px;
  border-bottom: 1px solid #e5e7eb;
  background: #ffffff;
}

.app-nav button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 38px;
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 0 12px;
  color: #4b5563;
  background: transparent;
  font-weight: 700;
}

.app-nav button.active {
  border-color: #d1d5db;
  color: #111827;
  background: #f9fafb;
}
</style>
