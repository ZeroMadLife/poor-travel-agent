<script setup lang="ts">
import { computed } from 'vue'
import {
  CheckCircle2,
  ChevronDown,
  Circle,
  Clock3,
  FilePenLine,
  Terminal,
  Wrench,
  XCircle,
} from 'lucide-vue-next'
import type { CodingRunAuditStep, CodingRunAuditSummary } from '../../../types/api'
import type { TimelineTool } from '../../../stores/codingTimeline'

const props = withDefaults(defineProps<{
  runId: string
  tools: TimelineTool[]
  audit?: CodingRunAuditSummary
  active?: boolean
  pendingTool?: string
}>(), {
  audit: undefined,
  active: false,
  pendingTool: '',
})

const steps = computed<CodingRunAuditStep[]>(() => {
  if (props.audit?.steps.length) return props.audit.steps
  return props.tools.map((tool) => fallbackStep(tool))
})

const currentStep = computed(() => [...steps.value].reverse().find((step) => (
  step.status === 'running' || step.status === 'waiting'
)))

const headline = computed(() => {
  if (props.pendingTool) return `等待确认 · ${props.pendingTool}`
  if (props.active && currentStep.value) {
    const prefix = currentStep.value.status === 'waiting' ? '等待确认' : '正在执行'
    return `${prefix} · ${currentStep.value.action_summary}`
  }
  if (props.audit) return props.audit.headline
  const failed = steps.value.filter((step) => step.status === 'error').length
  if (failed) return `运行过程 · ${steps.value.length} 项 · ${failed} 项失败`
  return `运行过程 · ${steps.value.length} 项`
})

const durationLabel = computed(() => formatDuration(props.audit?.duration_ms ?? 0))
const changedFiles = computed(() => props.audit?.changed_files ?? [])

function fallbackStep(tool: TimelineTool): CodingRunAuditStep {
  const args = safeArguments(tool.tool, tool.args)
  return {
    tool: tool.tool,
    status: tool.status === 'running' || tool.status === 'blocked'
      ? (tool.status === 'blocked' ? 'waiting' : 'running')
      : tool.is_error || tool.status === 'error' ? 'error' : 'completed',
    action_summary: actionSummary(tool.tool, args),
    result_summary: tool.is_error ? '执行失败' : tool.result ? shellResultSummary(tool.result) : '执行中',
    duration_ms: 0,
    arguments_preview: JSON.stringify(args, null, 2),
    result_preview: tool.tool === 'read_file'
      ? '已读取文件内容（摘要不展示正文）'
      : redactAndClip(tool.result),
    arguments_truncated: false,
    result_truncated: tool.result.length > 1200,
  }
}

function safeArguments(tool: string, args: Record<string, unknown>) {
  return Object.fromEntries(Object.entries(args).map(([key, value]) => {
    const normalized = key.toLowerCase().replaceAll('-', '_')
    if (/(api_?key|authorization|cookie|credential|password|secret|token)/.test(normalized)) {
      return [key, '[REDACTED]']
    }
    if (['content', 'diff', 'env', 'input', 'patch', 'text'].includes(normalized)) {
      return [key, '[OMITTED]']
    }
    if (tool === 'run_shell' && key === 'command' && typeof value === 'string') {
      return [key, redactText(value)]
    }
    return [key, value]
  }))
}

function actionSummary(tool: string, args: Record<string, unknown>) {
  const path = stringArg(args, 'path')
  if (tool === 'read_file') return `读取 ${path || '文件'}`
  if (tool === 'list_files') return `列出 ${path || '.'}`
  if (tool === 'search') return `搜索 ${stringArg(args, 'pattern') || path || '工作区'}`
  if (tool === 'write_file') return `写入 ${path || '文件'}`
  if (tool === 'patch_file') return `修改 ${path || '文件'}`
  if (tool === 'run_shell') return `执行 ${stringArg(args, 'command') || 'shell 命令'}`
  return `调用 ${tool}`
}

function stringArg(args: Record<string, unknown>, key: string) {
  const value = args[key]
  return typeof value === 'string' ? value.trim() : ''
}

function shellResultSummary(result: string) {
  const match = result.match(/^exit_code:\s*(-?\d+)$/m)
  return match ? `退出码 ${match[1]}` : '执行完成'
}

function redactText(text: string) {
  return text
    .replace(/(authorization\s*:\s*)(?:bearer\s+|basic\s+)?[^\s'"\n]+/gi, '$1[REDACTED]')
    .replace(/\bbearer\s+[A-Za-z0-9._~+/=-]+/gi, 'Bearer [REDACTED]')
    .replace(/\b([A-Z][A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD))\s*=\s*[^\s]+/gi, '$1=[REDACTED]')
}

function redactAndClip(text: string) {
  const redacted = redactText(text)
  if (redacted.length <= 1200) return redacted
  return `${redacted.slice(0, 880).trimEnd()}\n… 省略 ${redacted.length - 1200} 字符 …\n${redacted.slice(-320).trimStart()}`
}

function formatDuration(milliseconds: number) {
  if (!milliseconds) return ''
  if (milliseconds < 1000) return `${milliseconds}ms`
  if (milliseconds < 60_000) return `${Math.max(1, Math.round(milliseconds / 1000))}s`
  const minutes = Math.floor(milliseconds / 60_000)
  const seconds = Math.round((milliseconds % 60_000) / 1000)
  return `${minutes}m ${seconds}s`
}

function statusLabel(status: string) {
  if (status === 'running') return '执行中'
  if (status === 'waiting') return '等待确认'
  if (status === 'error') return '失败'
  return '已完成'
}

function statusIcon(status: string) {
  if (status === 'error') return XCircle
  if (status === 'completed') return CheckCircle2
  return Circle
}

function commandPreview(step: CodingRunAuditStep) {
  if (step.tool !== 'run_shell' || !step.arguments_preview) return ''
  try {
    const args = JSON.parse(step.arguments_preview) as Record<string, unknown>
    const command = typeof args.command === 'string' ? args.command.trim() : ''
    return command ? redactText(command).slice(0, 220) : ''
  } catch {
    return ''
  }
}
</script>

<template>
  <details class="run-trace" :data-run-id="runId">
    <summary>
      <span class="trace-icon" :class="{ active }">
        <Wrench :size="14" />
      </span>
      <span class="trace-headline">{{ headline }}</span>
      <span v-if="durationLabel" class="trace-duration"><Clock3 :size="12" />{{ durationLabel }}</span>
      <span v-if="changedFiles.length" class="trace-files"><FilePenLine :size="12" />{{ changedFiles.length }}</span>
      <ChevronDown class="trace-chevron" :size="15" />
    </summary>

    <div class="trace-content">
      <ol class="trace-steps">
        <li v-for="(step, index) in steps" :key="`${step.tool}:${index}`" class="trace-step" :class="step.status">
          <header class="step-header">
            <component :is="statusIcon(step.status)" :size="14" />
            <Terminal v-if="step.tool === 'run_shell'" :size="13" />
            <strong>{{ step.action_summary }}</strong>
            <span>{{ statusLabel(step.status) }}</span>
            <time v-if="step.duration_ms">{{ formatDuration(step.duration_ms) }}</time>
          </header>
          <p v-if="commandPreview(step)" class="step-command"><Terminal :size="12" /><code>{{ commandPreview(step) }}</code></p>
          <p v-if="step.result_summary" class="step-result-summary">{{ step.result_summary }}</p>
        </li>
      </ol>
      <p v-if="steps.length === 0" class="trace-empty">尚无工具步骤</p>
      <div v-if="changedFiles.length" class="changed-files">
        <strong>变更文件</strong>
        <span v-for="path in changedFiles" :key="path">{{ path }}</span>
      </div>
    </div>
  </details>
</template>

<style scoped>
.run-trace { width:100%; margin:0 0 14px; border:1px solid var(--sage-border); border-radius:var(--sage-radius); background:var(--sage-surface); }
.run-trace summary { display:grid; grid-template-columns:24px minmax(0,1fr) auto auto 18px; align-items:center; gap:8px; min-height:38px; padding:0 10px; color:var(--sage-text-secondary); cursor:pointer; list-style:none; font-size:11px; }
.run-trace summary::-webkit-details-marker { display:none; }
.run-trace summary:hover { background:var(--sage-surface-muted); }
.trace-icon { display:grid; place-items:center; width:22px; height:22px; border-radius:var(--sage-radius-sm); color:var(--sage-text-muted); background:var(--sage-surface-muted); }
.trace-icon.active { color:var(--sage-warning); }
.trace-headline { min-width:0; overflow:hidden; color:var(--sage-text-secondary); font-weight:650; text-overflow:ellipsis; white-space:nowrap; }
.trace-duration,.trace-files { display:inline-flex; align-items:center; gap:4px; color:var(--sage-text-muted); font-family:var(--sage-font-mono); font-size:10px; white-space:nowrap; }
.trace-chevron { color:var(--sage-text-muted); transition:transform .16s ease; }
.run-trace[open] .trace-chevron { transform:rotate(180deg); }
.trace-content { border-top:1px solid var(--sage-border); }
.trace-steps { display:grid; gap:0; margin:0; padding:0; list-style:none; }
.trace-step { min-width:0; padding:9px 12px 10px; border-bottom:1px solid var(--sage-border); }
.trace-step:last-child { border-bottom:0; }
.step-header { display:grid; grid-template-columns:16px auto minmax(0,1fr) auto auto; align-items:center; gap:6px; min-height:22px; color:var(--sage-text-muted); }
.step-header strong { min-width:0; overflow:hidden; color:var(--sage-text-secondary); font-size:11px; text-overflow:ellipsis; white-space:nowrap; }
.step-header span,.step-header time { font-size:10px; white-space:nowrap; }
.trace-step.completed .step-header > svg:first-child { color:var(--sage-success); }
.trace-step.running .step-header > svg:first-child,.trace-step.waiting .step-header > svg:first-child { color:var(--sage-warning); }
.trace-step.error .step-header > svg:first-child { color:var(--sage-danger); }
.step-command { display:flex; align-items:flex-start; gap:5px; margin:5px 0 0 22px; color:var(--sage-text-muted); font-family:var(--sage-font-mono); font-size:10px; line-height:1.45; }
.step-command svg { flex:none; margin-top:1px; }
.step-command code { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.step-result-summary { margin:4px 0 0 22px; color:var(--sage-text-muted); font-size:10px; }
.trace-empty { margin:0; padding:12px; color:var(--sage-text-muted); font-size:11px; }
.changed-files { display:flex; flex-wrap:wrap; gap:5px 10px; padding:9px 12px; border-top:1px solid var(--sage-border); color:var(--sage-text-muted); font-size:10px; }
.changed-files strong { color:var(--sage-text-secondary); }
.changed-files span { font-family:var(--sage-font-mono); overflow-wrap:anywhere; }
@media (max-width:640px) { .run-trace summary { grid-template-columns:24px minmax(0,1fr) auto 18px; }.trace-files { display:none; }.step-header { grid-template-columns:16px auto minmax(0,1fr) auto; }.step-header time { display:none; } }
@media (prefers-reduced-motion:reduce) { .trace-chevron { transition:none; } }
</style>
