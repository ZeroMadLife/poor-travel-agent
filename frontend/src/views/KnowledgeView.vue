<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Check, FilePlus2, RotateCcw, X } from 'lucide-vue-next'
import {
  fetchKnowledgePages,
  fetchKnowledgeProposals,
  fetchKnowledgeSummary,
  ingestKnowledgeSource,
  proposeKnowledgeRollback,
  transitionKnowledgeProposal,
} from '../api/knowledge'
import { AssistantSectionView } from '../components/assistant'
import type { KnowledgePage, KnowledgeProposal, KnowledgeWorkspaceSummary } from '../types/api'

const summary = ref<KnowledgeWorkspaceSummary | null>(null)
const proposals = ref<KnowledgeProposal[]>([])
const pages = ref<KnowledgePage[]>([])
const loading = ref(true)
const error = ref('')
const relativePath = ref('')
const selectedRoot = ref('')
const busy = ref<Record<string, boolean>>({})

const selectedSource = computed(() =>
  summary.value?.source_roots.find((item) => item.root_id === selectedRoot.value),
)

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    const [nextSummary, nextProposals, nextPages] = await Promise.all([
      fetchKnowledgeSummary(),
      fetchKnowledgeProposals(),
      fetchKnowledgePages(),
    ])
    summary.value = nextSummary
    proposals.value = nextProposals
    pages.value = nextPages
    if (!selectedRoot.value) selectedRoot.value = nextSummary.source_roots[0]?.root_id || ''
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    loading.value = false
  }
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

onMounted(refresh)
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
        <div><strong>{{ summary.pending_proposal_count }}</strong><span>待审核</span></div>
        <div><strong>{{ summary.workspace_name }}</strong><span>Git 工作区</span></div>
      </section>

      <section class="stage-content ingest-section">
        <div><h2>导入来源</h2><p>{{ selectedSource?.label || '尚未配置来源' }}</p></div>
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
            placeholder="例如：45-V7-P1.1共享Shell与对话形变源码复盘.md"
            :disabled="busy.ingest || !selectedRoot"
          />
          <button type="submit" :disabled="busy.ingest || !relativePath.trim() || !selectedRoot">
            <FilePlus2 :size="16" />{{ busy.ingest ? '正在生成提案' : '生成摄取提案' }}
          </button>
        </form>
      </section>

      <section class="knowledge-section" aria-labelledby="proposal-title">
        <header><div><span>Review queue</span><h2 id="proposal-title">待审核知识更新</h2></div><strong>{{ proposals.length }}</strong></header>
        <p v-if="proposals.length === 0" class="empty-copy">当前没有待审核提案。导入来源后，Wiki 不会立即变化。</p>
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
.knowledge-error,.knowledge-state { margin:22px 0 0; padding:10px 12px; border-left:3px solid var(--sage-coral); background:var(--sage-danger-bg); color:var(--sage-text-secondary); font-size:var(--sage-font-sm); }.knowledge-state { border-color:var(--sage-source); background:var(--sage-source-bg); }.knowledge-metrics { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); border-bottom:1px solid var(--sage-border); }.knowledge-metrics div { min-width:0; padding:24px 18px; border-right:1px solid var(--sage-border); }.knowledge-metrics div:last-child { border-right:0; }.knowledge-metrics strong,.knowledge-metrics span { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.knowledge-metrics strong { font-size:19px; }.knowledge-metrics span { margin-top:5px; color:var(--sage-text-muted); font-size:var(--sage-font-xs); }.ingest-section>div p { margin-top:5px; font-size:var(--sage-font-xs); }.ingest-form { display:grid; grid-template-columns:190px minmax(0,1fr) auto; gap:8px; }.ingest-form select,.ingest-form input { min-width:0; height:38px; border:1px solid var(--sage-border-strong); border-radius:var(--sage-radius-sm); background:var(--sage-surface); color:var(--sage-text); padding:0 10px; }.ingest-form button,.proposal-actions button,.page-row button { display:inline-flex; align-items:center; justify-content:center; gap:6px; min-height:34px; border:1px solid var(--sage-border-strong); border-radius:var(--sage-radius-sm); background:var(--sage-surface); color:var(--sage-text); padding:0 12px; font-weight:650; }.ingest-form button,.proposal-actions .approve { border-color:var(--sage-source); background:var(--sage-source); color:white; }.knowledge-section { padding:30px 0; border-bottom:1px solid var(--sage-border); }.knowledge-section>header { display:flex; align-items:end; justify-content:space-between; gap:16px; margin-bottom:18px; }.knowledge-section>header span { color:var(--sage-text-muted); font-size:var(--sage-font-xs); text-transform:uppercase; }.knowledge-section h2 { margin:5px 0 0; font-size:var(--sage-font-lg); }.knowledge-section>header>strong { color:var(--sage-source); font-size:22px; }.empty-copy { color:var(--sage-text-muted); }.proposal-row,.page-row { padding:18px 0; border-top:1px solid var(--sage-border); }.proposal-heading { display:flex; justify-content:space-between; gap:18px; }.proposal-heading strong,.proposal-heading span,.page-row>div strong,.page-row>div code { display:block; }.proposal-heading span,.proposal-heading code,.page-row code { margin-top:5px; color:var(--sage-text-muted); font-size:var(--sage-font-xs); }.proposal-row pre { max-height:320px; margin:14px 0; overflow:auto; border:1px solid var(--sage-border); border-radius:var(--sage-radius-sm); background:var(--sage-code-bg); color:var(--sage-code-text); padding:13px; font-size:12px; line-height:1.55; }.proposal-actions { display:flex; justify-content:flex-end; gap:8px; }.proposal-actions .reject { color:var(--sage-coral); }.page-row ol { margin:14px 0 0; padding:0; list-style:none; }.page-row li { display:flex; align-items:center; justify-content:space-between; gap:12px; min-height:38px; border-top:1px dashed var(--sage-border); color:var(--sage-text-secondary); font-size:var(--sage-font-sm); }.page-row em { color:var(--sage-success); font-style:normal; font-weight:650; }button:disabled,input:disabled,select:disabled { opacity:.5; cursor:not-allowed; }
@media (max-width:760px) { .knowledge-metrics { grid-template-columns:repeat(2,minmax(0,1fr)); }.knowledge-metrics div:nth-child(2) { border-right:0; }.ingest-form { grid-template-columns:1fr; }.proposal-heading { flex-direction:column; gap:4px; }.proposal-actions { justify-content:stretch; }.proposal-actions button { flex:1; }.page-row li { align-items:flex-start; flex-direction:column; padding:9px 0; } }
</style>
