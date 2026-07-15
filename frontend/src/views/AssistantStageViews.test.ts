import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, expect, it, vi } from 'vitest'
import {
  fetchKnowledgePages,
  fetchKnowledgeProposals,
  fetchKnowledgeSummary,
  ingestKnowledgeSource,
  transitionKnowledgeProposal,
} from '../api/knowledge'
import KnowledgeView from './KnowledgeView.vue'

vi.mock('../api/knowledge', () => ({
  fetchKnowledgePages: vi.fn(),
  fetchKnowledgeProposals: vi.fn(),
  fetchKnowledgeSummary: vi.fn(),
  ingestKnowledgeSource: vi.fn(),
  proposeKnowledgeRollback: vi.fn(),
  transitionKnowledgeProposal: vi.fn(),
}))

const summary = {
  status: 'ready' as const,
  workspace_name: 'Sage-knowledge',
  source_count: 1,
  wiki_page_count: 0,
  pending_proposal_count: 1,
  last_synced_at: null,
  source_roots: [{ root_id: 'sage-learning', kind: 'obsidian' as const, label: 'Sage Learning' }],
}

const proposal = {
  proposal_id: 'kprop-1', source_root_id: 'sage-learning', source_kind: 'obsidian',
  source_relative_path: 'harness.md', source_revision: 'sha256:abc', raw_path: 'raw/source.md',
  page_id: 'page-1', target_path: 'wiki/sources/harness.md', title: 'Agent Harness',
  base_page_revision: '', change_kind: 'ingest' as const, status: 'pending' as const,
  projection_status: 'pending' as const, revision: 0, error: null,
  diff: '+可审核知识', diff_truncated: false, created_at: '', updated_at: '',
}

beforeEach(() => {
  vi.mocked(fetchKnowledgeSummary).mockReset().mockResolvedValue(summary)
  vi.mocked(fetchKnowledgeProposals).mockReset().mockResolvedValue([proposal])
  vi.mocked(fetchKnowledgePages).mockReset().mockResolvedValue([])
  vi.mocked(ingestKnowledgeSource).mockReset().mockResolvedValue(proposal)
  vi.mocked(transitionKnowledgeProposal).mockReset().mockResolvedValue({
    ...proposal, status: 'approved', projection_status: 'complete', revision: 1,
  })
})

async function mountKnowledge() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/knowledge', component: KnowledgeView }],
  })
  await router.push('/knowledge')
  const wrapper = mount(KnowledgeView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

it('renders real knowledge status and review controls', async () => {
  const wrapper = await mountKnowledge()

  expect(wrapper.text()).toContain('Sage-knowledge')
  expect(wrapper.text()).toContain('Agent Harness')
  expect(wrapper.text()).toContain('可审核知识')
  expect(wrapper.find('input[aria-label="来源相对路径"]').exists()).toBe(true)
  expect(wrapper.get('button.approve').text()).toContain('批准并提交')
  wrapper.unmount()
})

it('creates an ingest proposal and approves a pending proposal', async () => {
  const wrapper = await mountKnowledge()
  await wrapper.get('input[aria-label="来源相对路径"]').setValue('new.md')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(ingestKnowledgeSource).toHaveBeenCalledWith('sage-learning', 'new.md')

  await wrapper.get('button.approve').trigger('click')
  await flushPromises()
  expect(transitionKnowledgeProposal).toHaveBeenCalledWith('kprop-1', 'approve', 0)
  wrapper.unmount()
})
