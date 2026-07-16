<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import {
  Check,
  Database,
  FilePlus2,
  FolderUp,
  RotateCcw,
  RotateCw,
  Search,
  Sparkles,
  Square,
  X,
} from 'lucide-vue-next'
import {
  applyPendingKnowledgeMigration,
  buildKnowledgeJobStreamUrl,
  cancelKnowledgeJob,
  createKnowledgeJob,
  fetchKnowledgeJob,
  fetchKnowledgeJobs,
  fetchKnowledgeIndex,
  fetchPendingKnowledgeMigration,
  fetchKnowledgePages,
  fetchKnowledgeProposals,
  fetchKnowledgeSummary,
  ingestKnowledgeSource,
  parseKnowledgeJobEvent,
  proposeKnowledgeRollback,
  rebuildKnowledgeIndex,
  retryKnowledgeJobItem,
  searchKnowledge,
  transitionKnowledgeProposal,
  undoKnowledgeAutoApply,
} from '../api/knowledge'
import { AssistantSectionView } from '../components/assistant'
import type {
  KnowledgeJob,
  KnowledgeIndexSummary,
  KnowledgeMigrationPlan,
  KnowledgeMigrationResult,
  KnowledgePage,
  KnowledgeProposal,
  KnowledgeRetrieval,
  KnowledgeWorkspaceSummary,
} from '../types/api'

const summary = ref<KnowledgeWorkspaceSummary | null>(null)
const proposals = ref<KnowledgeProposal[]>([])
const autoApplied = ref<KnowledgeProposal[]>([])
const pages = ref<KnowledgePage[]>([])
const jobs = ref<KnowledgeJob[]>([])
const indexSummary = ref<KnowledgeIndexSummary | null>(null)
const migrationPlan = ref<KnowledgeMigrationPlan | null>(null)
const migrationResult = ref<KnowledgeMigrationResult | null>(null)
const retrieval = ref<KnowledgeRetrieval | null>(null)
const retrievalQuery = ref('')
const retrievalError = ref('')
const jobsAvailable = ref(true)
const loading = ref(true)
const error = ref('')
const relativePath = ref('')
const relativeDirectory = ref('.')
const selectedRoot = ref('')
const busy = ref<Record<string, boolean>>({})
let pollTimer: ReturnType<typeof setInterval> | null = null
const jobSockets = new Map<string, WebSocket>()

const activeJobs = computed(() => jobs.value.filter((job) => !isTerminal(job.status)))
const migrationActionCount = computed(() => {
  const plan = migrationPlan.value
  return plan ? plan.auto_apply_count + plan.retire_count + plan.block_count : 0
})

const selectedSource = computed(() =>
  summary.value?.source_roots.find((item) => item.root_id === selectedRoot.value),
)

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    const [nextSummary, nextProposals, nextPages, nextMigrationPlan, nextIndex] = await Promise.all([
      fetchKnowledgeSummary(),
      fetchKnowledgeProposals(null),
      fetchKnowledgePages(),
      fetchPendingKnowledgeMigration(),
      fetchKnowledgeIndex(),
    ])
    const nextJobs = await fetchKnowledgeJobs().catch(() => {
      jobsAvailable.value = false
      return []
    })
    summary.value = nextSummary
    const migrationReviewIds = new Set(
      nextMigrationPlan.items
        .filter((item) => item.disposition === 'review')
        .map((item) => item.proposal_id),
    )
    proposals.value = nextProposals.filter(
      (proposal) => proposal.status === 'pending' && migrationReviewIds.has(proposal.proposal_id),
    )
    autoApplied.value = nextProposals.filter(
      (proposal) => proposal.policy_decision?.action === 'auto_apply',
    ).slice(0, 10)
    pages.value = nextPages
    migrationPlan.value = nextMigrationPlan
    indexSummary.value = nextIndex
    jobs.value = nextJobs
    syncJobStreams()
    if (!selectedRoot.value) selectedRoot.value = nextSummary.source_roots[0]?.root_id || ''
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    loading.value = false
  }
}

async function rebuildIndex() {
  busy.value = { ...busy.value, index: true }
  error.value = ''
  try {
    indexSummary.value = await rebuildKnowledgeIndex()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    const next = { ...busy.value }
    delete next.index
    busy.value = next
  }
}

async function retrieveEvidence() {
  const query = retrievalQuery.value.trim()
  if (!query) return
  busy.value = { ...busy.value, retrieval: true }
  retrievalError.value = ''
  try {
    retrieval.value = await searchKnowledge(query)
  } catch (reason) {
    retrievalError.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    const next = { ...busy.value }
    delete next.retrieval
    busy.value = next
  }
}

async function applyMigration() {
  const plan = migrationPlan.value
  if (!plan || migrationActionCount.value === 0) return
  busy.value = { ...busy.value, migration: true }
  error.value = ''
  try {
    migrationResult.value = await applyPendingKnowledgeMigration(plan.plan_id)
    await refresh()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    const next = { ...busy.value }
    delete next.migration
    busy.value = next
  }
}

async function createBatch() {
  if (!selectedRoot.value) return
  busy.value = { ...busy.value, batch: true }
  error.value = ''
  try {
    const job = await createKnowledgeJob(selectedRoot.value, relativeDirectory.value.trim() || '.')
    jobsAvailable.value = true
    jobs.value = [job, ...jobs.value]
    syncJobStreams()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    const next = { ...busy.value }
    delete next.batch
    busy.value = next
  }
}

async function refreshJobs() {
  if (!jobsAvailable.value) return
  try {
    jobs.value = await fetchKnowledgeJobs()
    syncJobStreams()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  }
}

async function cancelJob(job: KnowledgeJob) {
  const key = `cancel:${job.job_id}`
  busy.value = { ...busy.value, [key]: true }
  try {
    await cancelKnowledgeJob(job.job_id)
    await refreshJobs()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    const next = { ...busy.value }
    delete next[key]
    busy.value = next
  }
}

async function retryItem(job: KnowledgeJob, itemId: string) {
  const key = `retry:${itemId}`
  busy.value = { ...busy.value, [key]: true }
  try {
    await retryKnowledgeJobItem(job.job_id, itemId)
    await refreshJobs()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    const next = { ...busy.value }
    delete next[key]
    busy.value = next
  }
}

function syncJobStreams() {
  const active = new Set(activeJobs.value.map((job) => job.job_id))
  for (const [jobId, socket] of jobSockets) {
    if (!active.has(jobId)) {
      socket.close()
      jobSockets.delete(jobId)
    }
  }
  for (const job of activeJobs.value) {
    if (jobSockets.has(job.job_id)) continue
    const socket = new WebSocket(buildKnowledgeJobStreamUrl(job.job_id, job.latest_sequence))
    jobSockets.set(job.job_id, socket)
    socket.onmessage = async (message) => {
      try {
        const event = parseKnowledgeJobEvent(JSON.parse(String(message.data)), job.job_id)
        const current = jobs.value.find((item) => item.job_id === job.job_id)
        if (current && event.sequence <= current.latest_sequence) return
        const refreshed = await fetchKnowledgeJob(job.job_id, false)
        jobs.value = jobs.value.map((item) => item.job_id === job.job_id ? refreshed : item)
        if (isTerminal(refreshed.status)) {
          socket.close()
          await refreshJobs()
        }
      } catch (reason) {
        error.value = reason instanceof Error ? reason.message : String(reason)
      }
    }
    socket.onclose = () => {
      if (jobSockets.get(job.job_id) === socket) jobSockets.delete(job.job_id)
    }
  }
}

function isTerminal(status: string) {
  return ['completed', 'completed_with_errors', 'cancelled'].includes(status)
}

function jobPercent(job: KnowledgeJob) {
  return job.total_items ? Math.round((job.processed_items / job.total_items) * 100) : 100
}

function jobStatus(status: string) {
  return ({ queued: '排队中', running: '处理中', cancelling: '取消中', completed: '已完成', completed_with_errors: '部分失败', cancelled: '已取消' } as Record<string, string>)[status] || status
}

async function ingest() {
  const path = relativePath.value.trim()
  if (!selectedRoot.value || !path) return
  busy.value = { ...busy.value, ingest: true }
  error.value = ''
  try {
    await ingestKnowledgeSource(selectedRoot.value, path)
    relativePath.value = ''
    await refresh()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    const next = { ...busy.value }
    delete next.ingest
    busy.value = next
  }
}

async function decide(proposal: KnowledgeProposal, action: 'approve' | 'reject') {
  busy.value = { ...busy.value, [proposal.proposal_id]: true }
  error.value = ''
  try {
    await transitionKnowledgeProposal(proposal.proposal_id, action, proposal.revision)
    await refresh()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    const next = { ...busy.value }
    delete next[proposal.proposal_id]
    busy.value = next
  }
}

async function rollback(page: KnowledgePage, revisionId: string) {
  const key = `rollback:${page.page_id}`
  busy.value = { ...busy.value, [key]: true }
  error.value = ''
  try {
    await proposeKnowledgeRollback(page.page_id, revisionId, page.current_revision)
    await refresh()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    const next = { ...busy.value }
    delete next[key]
    busy.value = next
  }
}

async function undoAutoApply(proposal: KnowledgeProposal) {
  const revision = proposal.policy_decision?.applied_page_revision
  if (!revision) return
  const key = `undo:${proposal.proposal_id}`
  busy.value = { ...busy.value, [key]: true }
  error.value = ''
  try {
    await undoKnowledgeAutoApply(proposal.proposal_id, revision)
    await refresh()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    const next = { ...busy.value }
    delete next[key]
    busy.value = next
  }
}

onMounted(() => {
  void refresh()
  pollTimer = setInterval(() => void refreshJobs(), 2000)
})
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  for (const socket of jobSockets.values()) socket.close()
  jobSockets.clear()
})
</script>

<template>
  <AssistantSectionView
    eyebrow="Knowledge Workspace"
    title="知识库"
    description="来源保持不可变，Wiki 修改先生成 diff，批准和回滚都会形成新的 Git revision。"
    tone="source"
  >
    <p v-if="error" class="knowledge-error" role="alert">{{ error }}</p>
    <p v-if="loading" class="knowledge-state" role="status">正在读取知识空间...</p>

    <template v-else-if="summary">
      <section class="knowledge-metrics" aria-label="知识库状态">
        <div><strong>{{ summary.source_count }}</strong><span>来源</span></div>
        <div><strong>{{ summary.wiki_page_count }}</strong><span>Wiki 页面</span></div>
        <div><strong>{{ summary.pending_proposal_count }}</strong><span>待处理</span></div>
        <div><strong>{{ summary.workspace_name }}</strong><span>Git 工作区</span></div>
      </section>

      <section v-if="indexSummary" class="index-status" aria-label="检索索引状态">
        <Database :size="18" />
        <div>
          <strong>Hybrid Retrieval 索引{{ indexSummary.status === 'ready' ? '就绪' : '降级' }}</strong>
          <span>
            {{ indexSummary.indexed_revision_count }}/{{ indexSummary.revision_count }} revisions ·
            {{ indexSummary.active_chunk_count }} active chunks ·
            {{ indexSummary.embedding_model }}@{{ indexSummary.embedding_revision }}
          </span>
        </div>
        <button type="button" :disabled="busy.index" @click="rebuildIndex">
          <RotateCw :size="14" />{{ busy.index ? '正在重建' : '重建索引' }}
        </button>
      </section>

      <section class="retrieval-section" aria-labelledby="retrieval-title">
        <header>
          <div>
            <span>Grounded retrieval</span>
            <h2 id="retrieval-title">向知识库提问</h2>
            <p>先返回可追溯证据；没有命中时明确说明，不让 Agent 用猜测代替知识。</p>
          </div>
          <em v-if="retrieval?.status === 'evidence_found'">
            {{ retrieval.citations.length }} 条引用 · {{ retrieval.used_tokens }} tokens
          </em>
        </header>
        <form class="retrieval-form" @submit.prevent="retrieveEvidence">
          <Search :size="17" aria-hidden="true" />
          <input
            v-model="retrievalQuery"
            type="search"
            aria-label="知识库问题"
            placeholder="例如：Sage 的上下文压缩如何恢复？"
            :disabled="busy.retrieval"
          />
          <button type="submit" :disabled="busy.retrieval || !retrievalQuery.trim()">
            {{ busy.retrieval ? '正在检索' : '检索证据' }}
          </button>
        </form>
        <p v-if="retrievalError" class="retrieval-error" role="alert">{{ retrievalError }}</p>
        <div v-else-if="retrieval?.status === 'no_evidence'" class="no-evidence" role="status">
          <strong>知识库没有找到可用证据</strong>
          <span>Agent 会明确告知证据不足，不会把模型猜测包装成知识库结论。</span>
        </div>
        <ol v-else-if="retrieval?.citations.length" class="citation-list" aria-live="polite">
          <li v-for="citation in retrieval.citations" :key="citation.citation_id">
            <div class="citation-heading">
              <span class="citation-rank">{{ citation.rank }}</span>
              <div>
                <strong>{{ citation.title }}</strong>
                <span>{{ citation.heading_path.join(' / ') || '正文' }}</span>
              </div>
              <code>{{ citation.citation_id.slice(0, 18) }}</code>
            </div>
            <p>{{ citation.excerpt }}</p>
            <footer>
              <code>{{ citation.source_relative_path }}</code>
              <span>page {{ citation.page_revision.slice(0, 14) }}</span>
              <span>source {{ citation.source_revision.slice(0, 14) }}</span>
              <span v-if="citation.truncated">已按上下文预算截断</span>
            </footer>
          </li>
        </ol>
      </section>

      <section
        v-if="migrationPlan && migrationPlan.total > 0"
        class="migration-banner"
        aria-labelledby="migration-title"
      >
        <div class="migration-icon"><Sparkles :size="19" /></div>
        <div class="migration-copy">
          <strong id="migration-title">历史知识整理</strong>
          <p>
            无需逐条审核。可信本地解析会自动提交，缺失或旧版本来源会归档，
            只有异常记录保留给你确认。
          </p>
          <div class="migration-counts">
            <span>自动沉淀 {{ migrationPlan.auto_apply_count }}</span>
            <span>归档 {{ migrationPlan.retire_count }}</span>
            <span>异常 {{ migrationPlan.review_count }}</span>
            <span v-if="migrationPlan.block_count">拦截 {{ migrationPlan.block_count }}</span>
          </div>
        </div>
        <button
          v-if="migrationActionCount > 0"
          type="button"
          :disabled="busy.migration"
          @click="applyMigration"
        >
          <Sparkles :size="15" />
          {{ busy.migration ? '正在整理' : `一键整理 ${migrationActionCount} 条` }}
        </button>
        <em v-else>只剩 {{ migrationPlan.review_count }} 条异常</em>
      </section>

      <p v-if="migrationResult" class="migration-result" role="status">
        本次已自动沉淀 {{ migrationResult.auto_applied_count }} 条、归档
        {{ migrationResult.retired_count }} 条；{{ migrationResult.review_count }} 条保留确认，
        {{ migrationResult.error_count }} 条执行失败。
      </p>

      <section class="stage-content ingest-section">
        <div><h2>批量摄取目录</h2><p>{{ selectedSource?.label || '尚未配置来源' }} · 任务离开页面后仍会继续</p></div>
        <p v-if="!jobsAvailable" class="jobs-disabled" role="status">持久任务未启用。执行数据库迁移并设置 KNOWLEDGE_JOBS_ENABLED=true 后开放。</p>
        <form class="ingest-form" @submit.prevent="createBatch">
          <select v-model="selectedRoot" aria-label="批量来源目录" :disabled="busy.batch || !jobsAvailable">
            <option v-for="root in summary.source_roots" :key="root.root_id" :value="root.root_id">
              {{ root.label }} · {{ root.kind }}
            </option>
          </select>
          <input
            v-model="relativeDirectory"
            type="text"
            aria-label="来源相对目录"
            placeholder=". 或 03_项目/tourswarm"
            :disabled="busy.batch || !selectedRoot || !jobsAvailable"
          />
          <button type="submit" :disabled="busy.batch || !selectedRoot || !jobsAvailable">
            <FolderUp :size="16" />{{ busy.batch ? '正在扫描' : '创建持久任务' }}
          </button>
        </form>
      </section>

      <section class="knowledge-section jobs-section" aria-labelledby="jobs-title">
        <header><div><span>Durable ingestion</span><h2 id="jobs-title">批量任务</h2></div><strong>{{ jobs.length }}</strong></header>
        <p v-if="jobs.length === 0" class="empty-copy">尚无批量任务。目录会按 Markdown、HTML 和文本 PDF 拆分，失败项可单独重试。</p>
        <article v-for="job in jobs" :key="job.job_id" class="job-row">
          <div class="job-heading">
            <div><strong>{{ job.source_label }} / {{ job.relative_directory }}</strong><span>{{ jobStatus(job.status) }} · {{ job.processed_items }}/{{ job.total_items }}</span></div>
            <code>{{ job.job_id.slice(0, 18) }}</code>
          </div>
          <div class="job-progress" role="progressbar" :aria-valuenow="jobPercent(job)" aria-valuemin="0" aria-valuemax="100">
            <span :style="{ width: `${jobPercent(job)}%` }"></span>
          </div>
          <div class="job-counts">
            <span>成功 {{ job.succeeded_items }}</span><span>去重 {{ job.skipped_items }}</span><span>失败 {{ job.failed_items }}</span><span>取消 {{ job.cancelled_items }}</span>
            <button v-if="!isTerminal(job.status)" type="button" :disabled="busy[`cancel:${job.job_id}`]" @click="cancelJob(job)"><Square :size="13" />取消</button>
          </div>
          <ol v-if="job.items?.some((item) => item.status === 'dead_letter')" class="failed-items">
            <li v-for="item in job.items.filter((candidate) => candidate.status === 'dead_letter')" :key="item.item_id">
              <div><code>{{ item.relative_path }}</code><span>{{ item.error }}</span></div>
              <button type="button" :disabled="busy[`retry:${item.item_id}`]" @click="retryItem(job, item.item_id)"><RotateCw :size="13" />重试</button>
            </li>
          </ol>
        </article>
      </section>

      <section class="stage-content ingest-section single-ingest">
        <div><h2>单文件沉淀</h2><p>本地确定性解析自动提交；外部解析结果进入审核队列</p></div>
        <form class="ingest-form" @submit.prevent="ingest">
          <select v-model="selectedRoot" aria-label="来源目录" :disabled="busy.ingest">
            <option v-for="root in summary.source_roots" :key="root.root_id" :value="root.root_id">
              {{ root.label }} · {{ root.kind }}
            </option>
          </select>
          <input
            v-model="relativePath"
            type="text"
            aria-label="来源相对路径"
            placeholder="例如：notes/harness.md、docs/guide.html 或 reports/design.pdf"
            :disabled="busy.ingest || !selectedRoot"
          />
          <button type="submit" :disabled="busy.ingest || !relativePath.trim() || !selectedRoot">
            <FilePlus2 :size="16" />{{ busy.ingest ? '正在处理' : '导入并执行策略' }}
          </button>
        </form>
      </section>

      <section class="knowledge-section" aria-labelledby="auto-title">
        <header><div><span>Autonomous deposits</span><h2 id="auto-title">最近自动沉淀</h2></div><strong>{{ autoApplied.length }}</strong></header>
        <p v-if="autoApplied.length === 0" class="empty-copy">本地确定性解析的私有来源会自动形成 Git revision，并可在后续修改前一键撤销。</p>
        <article v-for="proposal in autoApplied" :key="proposal.proposal_id" class="auto-row">
          <div>
            <strong>{{ proposal.title }}</strong>
            <span>低风险 · {{ proposal.source_relative_path }} · policy {{ proposal.policy_decision?.policy_version }}</span>
          </div>
          <button
            v-if="proposal.policy_decision?.undo_available"
            type="button"
            :disabled="busy[`undo:${proposal.proposal_id}`]"
            @click="undoAutoApply(proposal)"
          ><RotateCcw :size="14" />撤销自动沉淀</button>
          <em v-else>{{ proposal.policy_decision?.undone_at ? '已撤销' : '不可撤销' }}</em>
        </article>
      </section>

      <section class="knowledge-section" aria-labelledby="proposal-title">
        <header><div><span>Exceptions only</span><h2 id="proposal-title">异常与需确认</h2></div><strong>{{ proposals.length }}</strong></header>
        <p v-if="proposals.length === 0" class="empty-copy">当前没有异常。可信本地来源会自动沉淀并保留撤销入口。</p>
        <article v-for="proposal in proposals" :key="proposal.proposal_id" class="proposal-row">
          <div class="proposal-heading">
            <div><strong>{{ proposal.title }}</strong><span>{{ proposal.change_kind === 'rollback' ? '回滚提案' : proposal.source_relative_path }}</span></div>
            <code>{{ proposal.source_revision.slice(0, 22) }}</code>
          </div>
          <pre><code>{{ proposal.diff || '内容与当前页面一致' }}</code></pre>
          <div class="proposal-actions">
            <button type="button" class="reject" :disabled="busy[proposal.proposal_id]" @click="decide(proposal, 'reject')"><X :size="15" />拒绝</button>
            <button type="button" class="approve" :disabled="busy[proposal.proposal_id]" @click="decide(proposal, 'approve')"><Check :size="15" />批准并提交</button>
          </div>
        </article>
      </section>

      <section class="knowledge-section" aria-labelledby="pages-title">
        <header><div><span>Versioned wiki</span><h2 id="pages-title">已批准页面</h2></div><strong>{{ pages.length }}</strong></header>
        <p v-if="pages.length === 0" class="empty-copy">批准首个提案后，页面和 Git revision 会出现在这里。</p>
        <article v-for="page in pages" :key="page.page_id" class="page-row">
          <div><strong>{{ page.title }}</strong><code>{{ page.path }}</code></div>
          <ol>
            <li v-for="revision in [...page.revisions].reverse()" :key="revision.revision_id">
              <span>r{{ revision.sequence }} · {{ revision.change_kind }} · {{ revision.git_commit.slice(0, 8) }}</span>
              <button
                v-if="revision.revision_id !== page.current_revision"
                type="button"
                :disabled="busy[`rollback:${page.page_id}`]"
                @click="rollback(page, revision.revision_id)"
              ><RotateCcw :size="14" />生成回滚提案</button>
              <em v-else>当前</em>
            </li>
          </ol>
        </article>
      </section>
    </template>
  </AssistantSectionView>
</template>

<style scoped>
.jobs-disabled { margin:0 0 9px; color:var(--sage-coral); font-size:var(--sage-font-xs); }
  .index-status { display:grid; grid-template-columns:auto minmax(0,1fr) auto; align-items:center; gap:12px; padding:13px 0; border-bottom:1px solid var(--sage-border); color:var(--sage-source); }.index-status div { display:flex; flex-direction:column; min-width:0; gap:3px; }.index-status strong { color:var(--sage-text); font-size:var(--sage-font-sm); }.index-status span { overflow:hidden; color:var(--sage-text-muted); font-size:var(--sage-font-xs); text-overflow:ellipsis; white-space:nowrap; }.index-status button { display:inline-flex; align-items:center; gap:5px; min-height:32px; border:1px solid var(--sage-border-strong); border-radius:var(--sage-radius-sm); background:var(--sage-surface); color:var(--sage-text-secondary); padding:0 10px; }
  .retrieval-section { padding:30px 0; border-bottom:1px solid var(--sage-border); }.retrieval-section>header { display:flex; align-items:end; justify-content:space-between; gap:20px; }.retrieval-section>header span { color:var(--sage-source); font-size:var(--sage-font-xs); font-weight:700; text-transform:uppercase; }.retrieval-section h2 { margin:5px 0 0; font-size:var(--sage-font-lg); }.retrieval-section>header p { max-width:650px; margin:7px 0 0; color:var(--sage-text-secondary); font-size:var(--sage-font-sm); line-height:1.55; }.retrieval-section>header em { color:var(--sage-text-muted); font-size:var(--sage-font-xs); font-style:normal; white-space:nowrap; }.retrieval-form { display:grid; grid-template-columns:auto minmax(0,1fr) auto; align-items:center; gap:10px; margin-top:18px; border:1px solid var(--sage-border-strong); border-radius:var(--sage-radius); background:var(--sage-surface); padding:7px 7px 7px 12px; color:var(--sage-text-muted); }.retrieval-form:focus-within { border-color:var(--sage-source); box-shadow:0 0 0 3px var(--sage-source-bg); }.retrieval-form input { min-width:0; height:34px; border:0; outline:0; background:transparent; color:var(--sage-text); font:inherit; }.retrieval-form button { min-height:34px; border:1px solid var(--sage-source); border-radius:var(--sage-radius-sm); background:var(--sage-source); color:white; padding:0 14px; font-weight:700; }.retrieval-error,.no-evidence { margin:14px 0 0; padding:13px 14px; border-left:3px solid var(--sage-coral); background:var(--sage-danger-bg); color:var(--sage-text-secondary); }.no-evidence { border-color:var(--sage-review-strong); background:var(--sage-review-bg); }.no-evidence strong,.no-evidence span { display:block; }.no-evidence span { margin-top:4px; font-size:var(--sage-font-xs); }.citation-list { margin:18px 0 0; padding:0; list-style:none; }.citation-list>li { padding:17px 0; border-top:1px solid var(--sage-border); }.citation-heading { display:grid; grid-template-columns:28px minmax(0,1fr) auto; align-items:start; gap:10px; }.citation-rank { display:grid; place-items:center; width:26px; height:26px; border-radius:50%; background:var(--sage-source-bg); color:var(--sage-source); font-size:var(--sage-font-xs); font-weight:800; }.citation-heading strong,.citation-heading div>span { display:block; }.citation-heading div>span { margin-top:3px; color:var(--sage-text-muted); font-size:var(--sage-font-xs); }.citation-heading>code { color:var(--sage-text-muted); font-size:11px; }.citation-list>li>p { margin:11px 0; color:var(--sage-text-secondary); font-size:var(--sage-font-sm); line-height:1.65; white-space:pre-wrap; }.citation-list footer { display:flex; flex-wrap:wrap; gap:8px 14px; color:var(--sage-text-muted); font-size:11px; }.citation-list footer code { color:var(--sage-text-secondary); }
  .migration-banner { display:grid; grid-template-columns:auto minmax(0,1fr) auto; align-items:center; gap:14px; margin:22px 0 0; padding:16px; border:1px solid var(--sage-border-strong); border-radius:var(--sage-radius); background:var(--sage-source-bg); }.migration-icon { display:grid; place-items:center; width:38px; height:38px; border-radius:var(--sage-radius-sm); background:var(--sage-source); color:white; }.migration-copy strong { font-size:var(--sage-font-md); }.migration-copy p { margin:4px 0 0; color:var(--sage-text-secondary); font-size:var(--sage-font-sm); line-height:1.55; }.migration-counts { display:flex; flex-wrap:wrap; gap:12px; margin-top:8px; color:var(--sage-text-muted); font-size:var(--sage-font-xs); }.migration-banner button { display:inline-flex; align-items:center; justify-content:center; gap:6px; min-height:36px; border:1px solid var(--sage-source); border-radius:var(--sage-radius-sm); background:var(--sage-source); color:white; padding:0 13px; font-weight:650; }.migration-banner em { color:var(--sage-review-strong); font-size:var(--sage-font-sm); font-style:normal; font-weight:650; }.migration-result { margin:10px 0 0; color:var(--sage-success); font-size:var(--sage-font-sm); }
  .knowledge-error,.knowledge-state { margin:22px 0 0; padding:10px 12px; border-left:3px solid var(--sage-coral); background:var(--sage-danger-bg); color:var(--sage-text-secondary); font-size:var(--sage-font-sm); }.knowledge-state { border-color:var(--sage-source); background:var(--sage-source-bg); }.knowledge-metrics { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); border-bottom:1px solid var(--sage-border); }.knowledge-metrics div { min-width:0; padding:24px 18px; border-right:1px solid var(--sage-border); }.knowledge-metrics div:last-child { border-right:0; }.knowledge-metrics strong,.knowledge-metrics span { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.knowledge-metrics strong { font-size:19px; }.knowledge-metrics span { margin-top:5px; color:var(--sage-text-muted); font-size:var(--sage-font-xs); }.ingest-section>div p { margin-top:5px; font-size:var(--sage-font-xs); }.single-ingest { border-top:1px solid var(--sage-border); }.ingest-form { display:grid; grid-template-columns:190px minmax(0,1fr) auto; gap:8px; }.ingest-form select,.ingest-form input { min-width:0; height:38px; border:1px solid var(--sage-border-strong); border-radius:var(--sage-radius-sm); background:var(--sage-surface); color:var(--sage-text); padding:0 10px; }.ingest-form button,.proposal-actions button,.page-row button,.job-row button,.auto-row button { display:inline-flex; align-items:center; justify-content:center; gap:6px; min-height:34px; border:1px solid var(--sage-border-strong); border-radius:var(--sage-radius-sm); background:var(--sage-surface); color:var(--sage-text); padding:0 12px; font-weight:650; }.ingest-form button,.proposal-actions .approve { border-color:var(--sage-source); background:var(--sage-source); color:white; }.knowledge-section { padding:30px 0; border-bottom:1px solid var(--sage-border); }.knowledge-section>header { display:flex; align-items:end; justify-content:space-between; gap:16px; margin-bottom:18px; }.knowledge-section>header span { color:var(--sage-text-muted); font-size:var(--sage-font-xs); text-transform:uppercase; }.knowledge-section h2 { margin:5px 0 0; font-size:var(--sage-font-lg); }.knowledge-section>header>strong { color:var(--sage-source); font-size:22px; }.empty-copy { color:var(--sage-text-muted); }.proposal-row,.page-row,.job-row,.auto-row { padding:18px 0; border-top:1px solid var(--sage-border); }.auto-row { display:flex; align-items:center; justify-content:space-between; gap:16px; }.auto-row strong,.auto-row span { display:block; }.auto-row span { margin-top:5px; color:var(--sage-text-muted); font-size:var(--sage-font-xs); }.auto-row em { color:var(--sage-text-muted); font-style:normal; font-size:var(--sage-font-sm); }.proposal-heading,.job-heading { display:flex; justify-content:space-between; gap:18px; }.proposal-heading strong,.proposal-heading span,.page-row>div strong,.page-row>div code,.job-heading strong,.job-heading span { display:block; }.proposal-heading span,.proposal-heading code,.page-row code,.job-heading span,.job-heading code { margin-top:5px; color:var(--sage-text-muted); font-size:var(--sage-font-xs); }.job-progress { height:6px; margin:14px 0 10px; overflow:hidden; border-radius:3px; background:var(--sage-border); }.job-progress span { display:block; height:100%; background:var(--sage-source); transition:width .2s ease; }.job-counts { display:flex; align-items:center; gap:14px; color:var(--sage-text-muted); font-size:var(--sage-font-xs); }.job-counts button { margin-left:auto; min-height:28px; color:var(--sage-coral); }.failed-items { margin:12px 0 0; padding:0; list-style:none; }.failed-items li { display:flex; justify-content:space-between; align-items:center; gap:12px; padding:9px 0; border-top:1px dashed var(--sage-border); }.failed-items code,.failed-items span { display:block; }.failed-items span { margin-top:3px; color:var(--sage-coral); font-size:var(--sage-font-xs); }.proposal-row pre { max-height:320px; margin:14px 0; overflow:auto; border:1px solid var(--sage-border); border-radius:var(--sage-radius-sm); background:var(--sage-code-bg); color:var(--sage-code-text); padding:13px; font-size:12px; line-height:1.55; }.proposal-actions { display:flex; justify-content:flex-end; gap:8px; }.proposal-actions .reject { color:var(--sage-coral); }.page-row ol { margin:14px 0 0; padding:0; list-style:none; }.page-row li { display:flex; align-items:center; justify-content:space-between; gap:12px; min-height:38px; border-top:1px dashed var(--sage-border); color:var(--sage-text-secondary); font-size:var(--sage-font-sm); }.page-row em { color:var(--sage-success); font-style:normal; font-weight:650; }button:disabled,input:disabled,select:disabled { opacity:.5; cursor:not-allowed; }
@media (max-width:760px) { .knowledge-metrics { grid-template-columns:repeat(2,minmax(0,1fr)); }.knowledge-metrics div:nth-child(2) { border-right:0; }.index-status { grid-template-columns:auto minmax(0,1fr); }.index-status button { grid-column:1 / -1; justify-content:center; width:100%; }.retrieval-section>header { align-items:flex-start; flex-direction:column; gap:8px; }.retrieval-form { grid-template-columns:auto minmax(0,1fr); }.retrieval-form button { grid-column:1 / -1; width:100%; }.citation-heading { grid-template-columns:28px minmax(0,1fr); }.citation-heading>code { grid-column:2; overflow:hidden; text-overflow:ellipsis; }.migration-banner { grid-template-columns:auto minmax(0,1fr); align-items:start; }.migration-banner button,.migration-banner>em { grid-column:1 / -1; width:100%; }.ingest-form { grid-template-columns:1fr; }.proposal-heading,.job-heading { flex-direction:column; gap:4px; }.job-counts { flex-wrap:wrap; }.job-counts button { margin-left:0; }.failed-items li { align-items:flex-start; flex-direction:column; }.proposal-actions { justify-content:stretch; }.proposal-actions button { flex:1; }.page-row li { align-items:flex-start; flex-direction:column; padding:9px 0; } }
</style>
