import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { HarnessReviewBundle } from '../../../harness/reviewBundle'
import type { HarnessProjection } from '../../../harness/types'
import CodingHarnessWorkbench from './CodingHarnessWorkbench.vue'

function projection(): HarnessProjection {
  return {
    definitionId: 'sage.coding.practice',
    definitionVersion: 1,
    definitionMissing: false,
    runId: 'run-a',
    status: 'running',
    activeStageId: 'act',
    stages: [
      { id: 'receive', label: '接收目标', status: 'completed', visitCount: 1, lastSequence: 1, durationMs: 500 },
      { id: 'plan', label: '规划', status: 'completed', visitCount: 2, lastSequence: 2, durationMs: 1_200 },
      { id: 'act', label: '调用工具', status: 'running', visitCount: 1, lastSequence: 3, durationMs: 800 },
    ],
    transitions: [],
    visitedPath: ['receive', 'plan', 'act'],
    lastSequence: 3,
    runtimeResources: [{
      id: 'context-budget',
      kind: 'context',
      label: '上下文',
      detail: '420 / 32000 tokens',
      status: 'completed',
    }, {
      id: 'run-budget',
      kind: 'budget',
      label: '本轮预算',
      detail: '24k / 100k tokens · 3/24 模型 · 5/64 工具',
      status: 'completed',
    }],
  }
}

function reviewBundle(): HarnessReviewBundle {
  return {
    runId: 'run-a',
    evidence: {
      status: 'ready', query: 'checkpoint 恢复', omittedCount: 0,
      items: [{
        id: 'evidence-1', title: '持久化机制', source: 'knowledge/wiki.md',
        pageRevision: 'page-rev-18', excerpt: 'checkpoint 保存可恢复状态。',
      }],
    },
    practice: {
      status: 'complete', headline: '恢复练习已通过', toolCount: 3,
      completedToolCount: 3, failedToolCount: 0, approvalCount: 0,
      durationMs: 2_500, changedFiles: ['checkpointing.md'],
    },
    deposit: {
      status: 'review', proposalId: 'proposal-1', revision: 2,
      items: ['把恢复边界写入长期记忆'], source: 'run-a',
    },
  }
}

describe('CodingHarnessWorkbench', () => {
  it('projects a running timeline as active learning without inventing mastery', () => {
    const wrapper = mount(CodingHarnessWorkbench, {
      props: { projection: projection(), sessionTitle: '重构项目', toolCallCount: 3 },
    })

    expect(wrapper.attributes('data-run-id')).toBe('run-a')
    expect(wrapper.attributes('data-journey')).toBe('active')
    expect(wrapper.get('.goal-heading').text()).toContain('重构项目')
    expect(wrapper.get('.workbench-metrics').text()).toContain('运行中')
    expect(wrapper.get('.workbench-metrics').text()).toContain('2.5s')
    expect(wrapper.get('.workbench-metrics').text()).toContain('24k / 100k tokens')
    expect(wrapper.get('.workbench-metrics').text()).toContain('3')
    expect(wrapper.get('[aria-current="step"]').text()).toContain('调用工具')
    expect(wrapper.get('.workbench-mark').classes()).toContain('running')
    expect(wrapper.get('.evidence-summary').text()).toContain('尚未验证')
  })

  it('exposes failed and completed states on the workbench chrome', async () => {
    const current = projection()
    const wrapper = mount(CodingHarnessWorkbench, {
      props: { projection: { ...current, status: 'failed' }, sessionTitle: '验证状态' },
    })

    expect(wrapper.get('.workbench-mark').classes()).toContain('failed')
    expect(wrapper.get('.metric-state').text()).toContain('失败')

    await wrapper.setProps({ projection: { ...current, status: 'completed' } })
    expect(wrapper.get('.workbench-mark').classes()).toContain('completed')
    expect(wrapper.get('.metric-state').text()).toContain('已完成')
  })

  it('uses an honest goal-contract surface before the first run', () => {
    const current = projection()
    const wrapper = mount(CodingHarnessWorkbench, {
      props: {
        projection: {
          ...current, runId: '', status: 'idle', activeStageId: null,
          stages: [], visitedPath: [], lastSequence: 0,
        },
        sessionTitle: '成为独立交付 AI Agent 的工程师',
      },
    })

    expect(wrapper.attributes('data-journey')).toBe('contract')
    expect(wrapper.get('.contract-surface').text()).toContain('目标尚未确认')
    expect(wrapper.get('.contract-surface').text()).toContain('等待在对话中确认')
    expect(wrapper.get('.contract-surface').text()).not.toContain('42%')
  })

  it('shows deposit review only for a real pending proposal', () => {
    const wrapper = mount(CodingHarnessWorkbench, {
      props: {
        projection: { ...projection(), status: 'completed' },
        sessionTitle: '恢复机制研究', reviewBundle: reviewBundle(),
      },
    })

    expect(wrapper.attributes('data-journey')).toBe('review')
    expect(wrapper.get('.review-surface').text()).toContain('确认哪些内容进入长期系统')
    expect(wrapper.get('.review-surface').text()).toContain('1 条可追溯证据')
    expect(wrapper.get('.review-surface').text()).toContain('批准沉淀')
  })

  it('prioritizes connection recovery and shows the last sequence', () => {
    const wrapper = mount(CodingHarnessWorkbench, {
      props: {
        projection: projection(), sessionTitle: '恢复机制研究',
        connectionState: 'recovering',
      },
    })

    expect(wrapper.attributes('data-journey')).toBe('recovery')
    expect(wrapper.get('.recovery-surface').text()).toContain('sequence 3')
    expect(wrapper.get('.recovery-surface').text()).toContain('不重新标记已完成工具')
  })

  it('replays repeated stage events instead of collapsing them into one stage row', () => {
    const current = projection()
    const wrapper = mount(CodingHarnessWorkbench, {
      props: {
        projection: {
          ...current,
          stageEvents: [{
            eventId: 'event-1', stageId: 'act', label: '调用工具',
            detail: '第一次检索', status: 'completed', timestamp: '2026-07-18T10:00:00Z', sequence: 4,
          }, {
            eventId: 'event-2', stageId: 'act', label: '调用工具',
            detail: '第二次检索', status: 'running', timestamp: '2026-07-18T10:00:01Z', sequence: 5,
          }],
        },
        sessionTitle: '验证事件回放',
      },
    })

    expect(wrapper.get('.event-replay').text()).toContain('第一次检索')
    expect(wrapper.get('.event-replay').text()).toContain('第二次检索')
  })

  it('opens a traceable child operation from the runtime resource list', async () => {
    const current = projection()
    const wrapper = mount(CodingHarnessWorkbench, {
      props: {
        projection: {
          ...current,
          runtimeResources: [{
            id: 'agent:child-1', kind: 'agent', label: '子代理',
            detail: '比较两份文档', status: 'running',
            operationRef: { kind: 'coding_run', id: 'child-1' },
          }],
        },
        sessionTitle: '验证子代理',
      },
    })

    await wrapper.get('button[aria-label="查看子代理运行详情"]').trigger('click')
    expect(wrapper.emitted('openOperation')).toEqual([[{
      kind: 'coding_run', id: 'child-1',
    }]])
  })
})
