<script setup lang="ts">
import type { CodingApproval, CodingApprovalChoice } from '../types/api'

defineProps<{
  approval: CodingApproval
  busy?: boolean
}>()

const emit = defineEmits<{
  respond: [CodingApprovalChoice]
}>()
</script>

<template>
  <section class="approval-card" aria-label="Tool approval">
    <div class="approval-main">
      <p class="eyebrow">需要确认</p>
      <h2>{{ approval.tool }}</h2>
      <p class="description">{{ approval.description }}</p>
      <div v-if="approval.diff_preview?.length" class="diff-preview">
        <div
          v-for="(line, index) in approval.diff_preview"
          :key="index"
          :class="['diff-line', `diff-${line.type}`]"
        >
          <span class="diff-prefix">
            {{ line.type === 'add' ? '+' : line.type === 'remove' ? '-' : ' ' }}
          </span>
          <span>{{ line.text || ' ' }}</span>
        </div>
      </div>
      <pre v-else>{{ JSON.stringify(approval.args, null, 2) }}</pre>
    </div>
    <div class="actions">
      <button class="deny" :disabled="busy" @click="emit('respond', 'deny')">Deny</button>
      <button class="session" :disabled="busy" @click="emit('respond', 'session')">
        Allow session
      </button>
      <button class="always" :disabled="busy" @click="emit('respond', 'always')">
        Always
      </button>
      <button class="allow" :disabled="busy" @click="emit('respond', 'once')">Allow once</button>
    </div>
  </section>
</template>

<style scoped>
.approval-card {
  position: absolute;
  right: 18px;
  bottom: 96px;
  left: 18px;
  z-index: 5;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 14px;
  align-items: end;
  padding: 12px;
  border: 1px solid #f59e0b;
  border-radius: 8px;
  background: #fffbeb;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.16);
}

.approval-main {
  min-width: 0;
}

.eyebrow {
  margin: 0 0 4px;
  color: #92400e;
  font-size: 11px;
  font-weight: 700;
}

h2 {
  margin: 0 0 4px;
  color: #111827;
  font-size: 14px;
}

.description {
  margin: 0 0 8px;
  color: #374151;
  font-size: 13px;
}

pre {
  max-height: 110px;
  margin: 0;
  overflow: auto;
  color: #4b5563;
  font-size: 12px;
  white-space: pre-wrap;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

button {
  min-height: 32px;
  padding: 0 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.deny {
  border: 1px solid #d1d5db;
  color: #374151;
  background: #fff;
}

.allow {
  border: 1px solid #111827;
  color: #fff;
  background: #111827;
}

.session,
.always {
  border: 1px solid #d1d5db;
  color: #111827;
  background: #fff;
}

.diff-preview {
  max-height: 150px;
  overflow: auto;
  border: 1px solid #f0d9a4;
  border-radius: 6px;
  background: #fff;
  font-family: 'SF Mono', monospace;
  font-size: 12px;
}

.diff-line {
  display: grid;
  grid-template-columns: 18px 1fr;
  padding: 1px 6px;
  white-space: pre-wrap;
}

.diff-prefix {
  color: #6b7280;
  user-select: none;
}

.diff-add {
  color: #047857;
  background: #ecfdf5;
}

.diff-remove {
  color: #b91c1c;
  background: #fef2f2;
}

.diff-context {
  color: #4b5563;
}
</style>
