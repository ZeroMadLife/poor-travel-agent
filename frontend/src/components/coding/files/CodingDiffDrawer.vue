<script setup lang="ts">
import { ChevronDown, ChevronRight, X } from 'lucide-vue-next'
import { ref, watch } from 'vue'
import type { CodingFileDiff, CodingRunDiff } from '../../../types/api'

const props = defineProps<{
  diff: CodingRunDiff | null
  visible: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const expandedFile = ref<string | null>(null)

// Reset expanded state whenever the drawer is hidden so reopening starts fresh.
watch(
  () => props.visible,
  (visible) => {
    if (!visible) expandedFile.value = null
  },
)

function toggleFile(path: string) {
  expandedFile.value = expandedFile.value === path ? null : path
}

function statusLabel(status: CodingFileDiff['status']) {
  const labels: Record<CodingFileDiff['status'], string> = {
    added: '新增',
    modified: '修改',
    deleted: '删除',
  }
  return labels[status] || status
}

function statusClass(status: CodingFileDiff['status']) {
  return `status-${status}`
}

function fileTitle(file: CodingFileDiff): string {
  if (file.binary) return `${file.path} (二进制)`
  if (file.ignored_sensitive) return `${file.path} (含敏感内容,已隐藏)`
  return file.path
}
</script>

<template>
  <div v-if="visible" class="diff-backdrop" role="presentation" @click.self="emit('close')">
    <section
      class="diff-drawer"
      role="dialog"
      aria-modal="true"
      aria-label="运行变更"
    >
      <header class="diff-drawer-header">
        <div class="diff-drawer-title">
          <p class="eyebrow">运行变更</p>
          <h3>运行变更 ({{ diff?.file_count ?? 0 }} 个文件)</h3>
        </div>
        <button
          class="close-btn"
          type="button"
          aria-label="关闭变更面板"
          @click="emit('close')"
        >
          <X :size="16" />
        </button>
      </header>

      <div class="diff-drawer-body">
        <p v-if="diff?.truncated" class="diff-truncated-note">
          变更文件较多,部分文件未显示。
        </p>
        <p v-if="!diff || diff.changed_files.length === 0" class="diff-empty">
          暂无变更文件
        </p>

        <ul v-else class="file-list">
          <li v-for="file in diff.changed_files" :key="file.path" class="file-item">
            <button
              class="file-header"
              type="button"
              :disabled="file.binary || file.ignored_sensitive"
              :aria-expanded="expandedFile === file.path"
              @click="toggleFile(file.path)"
            >
              <component
                :is="expandedFile === file.path ? ChevronDown : ChevronRight"
                :size="13"
              />
              <span class="file-path">{{ fileTitle(file) }}</span>
              <span class="file-status" :class="statusClass(file.status)">
                {{ statusLabel(file.status) }}
              </span>
            </button>
            <div v-if="expandedFile === file.path" class="file-diff">
              <pre v-if="file.diff" class="diff-content">{{ file.diff }}</pre>
              <p v-else class="diff-placeholder">无 diff 内容</p>
            </div>
          </li>
        </ul>
      </div>
    </section>
  </div>
</template>

<style scoped>
.diff-backdrop {
  position: fixed;
  inset: 0;
  z-index: 30;
  display: flex;
  justify-content: flex-end;
  background: rgba(17, 24, 39, 0.32);
}

.diff-drawer {
  display: grid;
  grid-template-rows: auto 1fr;
  width: min(560px, 100%);
  height: 100%;
  border-left: 1px solid #d1d5db;
  background: #fff;
  box-shadow: -16px 0 48px rgba(15, 23, 42, 0.18);
}

.diff-drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-bottom: 1px solid #e5e7eb;
}

.diff-drawer-title .eyebrow {
  margin: 0 0 3px;
  color: #6b7280;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.diff-drawer-title h3 {
  margin: 0;
  color: #111827;
  font-size: 14px;
}

.close-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  min-height: 30px;
  padding: 0;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #374151;
  cursor: pointer;
}

.close-btn:hover {
  background: #f3f4f6;
}

.diff-drawer-body {
  overflow: auto;
  padding: 12px 14px;
  background: #fff;
}

.diff-truncated-note {
  margin: 0 0 10px;
  padding: 6px 10px;
  border-radius: 6px;
  background: #fef3c7;
  color: #92400e;
  font-size: 12px;
}

.diff-empty {
  margin: 0;
  color: #9ca3af;
  font-size: 13px;
}

.file-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.file-item {
  margin-bottom: 2px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fff;
}

.file-header {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 6px 8px;
  border: 0;
  background: transparent;
  cursor: pointer;
  text-align: left;
}

.file-header:disabled {
  cursor: default;
  color: #9ca3af;
}

.file-header:hover:not(:disabled) {
  background: #f9fafb;
  border-radius: 6px;
}

.file-path {
  flex: 1;
  overflow: hidden;
  color: #111827;
  font-size: 12px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-status {
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 700;
  background: #e5e7eb;
  color: #4b5563;
}

.file-status.status-added {
  background: #d1fae5;
  color: #065f46;
}

.file-status.status-modified {
  background: #fef3c7;
  color: #92400e;
}

.file-status.status-deleted {
  background: #fee2e2;
  color: #991b1b;
}

.file-diff {
  border-top: 1px solid #e5e7eb;
  padding: 8px 10px;
  background: #f9fafb;
}

.diff-content {
  margin: 0;
  max-height: 420px;
  overflow: auto;
  padding: 8px 10px;
  border-radius: 4px;
  background: #111827;
  color: #e5e7eb;
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.diff-placeholder {
  margin: 0;
  color: #9ca3af;
  font-size: 12px;
}
</style>
