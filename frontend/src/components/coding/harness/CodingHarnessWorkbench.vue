<script setup lang="ts">
import { Activity, Braces, Clock3, Wrench } from 'lucide-vue-next'
import { computed } from 'vue'
import type { HarnessProjection } from '../../../harness/types'
import HarnessRunStatus from '../../harness/HarnessRunStatus.vue'

const props = withDefaults(defineProps<{
  projection: HarnessProjection
  sessionTitle: string
  toolCallCount?: number
}>(), {
  toolCallCount: 0,
})

const statusLabel = computed(() => ({
  idle: '等待任务',
  running: 'LIVE',
  blocked: '等待确认',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
}[props.projection.status]))

const iterationCount = computed(() => {
  return props.projection.stages.find((stage) => stage.id === 'plan')?.visitCount ?? 0
})

const elapsedLabel = computed(() => {
  const elapsed = props.projection.stages.reduce((total, stage) => total + (stage.durationMs ?? 0), 0)
  if (elapsed < 1_000) return elapsed ? `${elapsed}ms` : '--'
  if (elapsed < 60_000) return `${(elapsed / 1_000).toFixed(elapsed < 10_000 ? 1 : 0)}s`
  const minutes = Math.floor(elapsed / 60_000)
  const seconds = Math.round((elapsed % 60_000) / 1_000)
  return `${minutes}m ${seconds}s`
})

const contextLabel = computed(() => {
  return props.projection.runtimeResources?.find((resource) => resource.kind === 'context')?.detail || '--'
})
</script>

<template>
  <section
    class="coding-harness-workbench"
    :data-run-id="projection.runId"
    :data-status="projection.status"
    aria-label="Harness 2.0 工作台"
  >
    <header class="workbench-header">
      <div class="workbench-title">
        <span class="workbench-mark" :class="projection.status"><Activity :size="15" /></span>
        <span class="workbench-title-copy">
          <strong>Harness 2.0</strong>
          <span :title="sessionTitle">{{ sessionTitle }}</span>
        </span>
      </div>
      <dl class="workbench-metrics">
        <div class="metric-state" :class="projection.status">
          <dt><Activity :size="13" />状态</dt>
          <dd>{{ statusLabel }}</dd>
        </div>
        <div>
          <dt><Clock3 :size="13" />耗时</dt>
          <dd>{{ elapsedLabel }}</dd>
        </div>
        <div>
          <dt><Braces :size="13" />迭代</dt>
          <dd>{{ iterationCount }}</dd>
        </div>
        <div>
          <dt><Wrench :size="13" />工具</dt>
          <dd>{{ toolCallCount }}</dd>
        </div>
        <div class="metric-context">
          <dt>上下文</dt>
          <dd :title="contextLabel">{{ contextLabel }}</dd>
        </div>
      </dl>
    </header>

    <div class="workbench-canvas">
      <HarnessRunStatus :projection="projection" :show-header="false" />
    </div>
  </section>
</template>

<style scoped>
.coding-harness-workbench {
  container: coding-harness / inline-size;
  display: grid;
  grid-template-rows: 62px minmax(0, 1fr);
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  color: var(--sage-text);
  background: var(--sage-surface);
}

.workbench-header {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  padding: 0 16px 0 18px;
  border-bottom: 1px solid var(--sage-border);
}

.workbench-title {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.workbench-mark {
  display: grid;
  place-items: center;
  flex: none;
  width: 30px;
  height: 30px;
  border: 1px solid var(--sage-border);
  border-radius: var(--sage-radius);
  color: var(--sage-text-muted);
  background: var(--sage-surface-raised);
}
.workbench-mark.running { border-color: color-mix(in srgb, var(--sage-success) 42%, var(--sage-border)); color: var(--sage-success); background: color-mix(in srgb, var(--sage-success-bg) 55%, var(--sage-surface)); }
.workbench-mark.completed { border-color: color-mix(in srgb, var(--sage-success) 28%, var(--sage-border)); color: var(--sage-success); }
.workbench-mark.blocked { border-color: color-mix(in srgb, var(--sage-warning) 42%, var(--sage-border)); color: var(--sage-warning); background: color-mix(in srgb, var(--sage-warning-bg) 55%, var(--sage-surface)); }
.workbench-mark.failed,
.workbench-mark.cancelled { border-color: color-mix(in srgb, var(--sage-danger) 42%, var(--sage-border)); color: var(--sage-danger); background: color-mix(in srgb, var(--sage-danger-bg) 55%, var(--sage-surface)); }
.workbench-title-copy { display: grid; min-width: 0; }
.workbench-title-copy strong { flex: none; font-size: var(--sage-font-md); line-height: 1.35; }
.workbench-title-copy > span {
  min-width: 0;
  max-width: 230px;
  overflow: hidden;
  color: var(--sage-text-muted);
  font-size: 11px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workbench-metrics {
  display: flex;
  align-self: stretch;
  min-width: 0;
  margin: 0 0 0 auto;
}

.workbench-metrics > div {
  display: grid;
  align-content: center;
  min-width: 70px;
  padding: 0 10px;
  border-left: 1px solid var(--sage-border);
}

.workbench-metrics dt,
.workbench-metrics dd { margin: 0; }
.workbench-metrics dt {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--sage-text-muted);
  font-size: 10px;
}
.workbench-metrics dd {
  margin-top: 2px;
  color: var(--sage-text-secondary);
  font-family: var(--sage-font-mono);
  font-size: var(--sage-font-xs);
}

.workbench-metrics .metric-state.running dd { color: var(--sage-success); }
.workbench-metrics .metric-state.completed dd { color: var(--sage-success); }
.workbench-metrics .metric-state.blocked dd { color: var(--sage-warning); }
.workbench-metrics .metric-state.failed dd,
.workbench-metrics .metric-state.cancelled dd { color: var(--sage-danger); }
.workbench-metrics .metric-context { min-width: 136px; max-width: 220px; }
.metric-context dd { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.workbench-canvas {
  min-width: 0;
  min-height: 0;
  overflow: auto;
  scrollbar-gutter: stable;
}

.workbench-canvas :deep(.harness-run-status) {
  min-height: 100%;
  padding: clamp(22px, 3vw, 34px) clamp(18px, 3.4vw, 40px);
}

@container coding-harness (max-width: 900px) {
  .metric-context { display: none !important; }
  .workbench-title-copy > span { max-width: 150px; }
}

@container coding-harness (max-width: 660px) {
  .workbench-header { gap: 8px; padding-right: 10px; padding-left: 12px; }
  .workbench-title { gap: 7px; }
  .workbench-mark { width: 28px; height: 28px; }
  .workbench-title-copy > span { display: none; }
  .workbench-metrics > div { min-width: 58px; padding: 0 7px; }
  .workbench-metrics dt svg { display: none; }
}

@media (max-width: 760px) {
  .coding-harness-workbench { grid-template-rows: auto minmax(0, 1fr); }
  .workbench-header { align-items: flex-start; flex-direction: column; gap: 10px; padding: 14px 16px; }
  .workbench-metrics { width: 100%; margin: 0; border-top: 1px solid var(--sage-border); }
  .workbench-metrics > div { flex: 1; min-width: 0; padding: 8px 8px 0; border-left: 0; }
  .workbench-metrics > div + div { border-left: 1px solid var(--sage-border); }
}
</style>
