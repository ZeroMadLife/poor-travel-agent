import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { CodingRunAuditSummary } from '../../../types/api'
import CodingRunTrace from './CodingRunTrace.vue'

const audit: CodingRunAuditSummary = {
  run_id: 'run-a',
  status: 'completed',
  headline: '运行完成 · 2 项工具 · 修改 1 个文件',
  tool_count: 2,
  completed_tool_count: 2,
  failed_tool_count: 0,
  approval_count: 1,
  duration_ms: 2250,
  changed_files: ['src/app.ts'],
  steps: [
    {
      tool: 'read_file',
      status: 'completed',
      action_summary: '读取 README.md',
      result_summary: '执行完成',
      duration_ms: 250,
      arguments_preview: '{"path":"README.md"}',
      result_preview: '已读取文件内容（摘要不展示正文）',
      arguments_truncated: false,
      result_truncated: false,
    },
    {
      tool: 'run_shell',
      status: 'completed',
      action_summary: '执行 npm test',
      result_summary: '退出码 0',
      duration_ms: 2000,
      arguments_preview: '{"command":"npm test"}',
      result_preview: 'exit_code: 0\n12 passed',
      arguments_truncated: false,
      result_truncated: false,
    },
  ],
}

describe('CodingRunTrace', () => {
  it('renders one collapsed run panel and reveals every step with one expansion', async () => {
    const wrapper = mount(CodingRunTrace, {
      props: { runId: 'run-a', tools: [], audit },
    })

    expect(wrapper.get('details').attributes('open')).toBeUndefined()
    expect(wrapper.get('summary').text()).toContain('运行完成 · 2 项工具 · 修改 1 个文件')
    expect(wrapper.findAll('details')).toHaveLength(1)

    await wrapper.get('summary').trigger('click')

    expect(wrapper.get('details').attributes('open')).toBe('')
    expect(wrapper.findAll('.trace-step')).toHaveLength(2)
    expect(wrapper.text()).toContain('退出码 0')
    expect(wrapper.text()).toContain('src/app.ts')
    expect(wrapper.text()).not.toContain('12 passed')
    expect(wrapper.findAll('.trace-step details')).toHaveLength(0)
  })

  it('shows the current action while active and keeps secret-shaped fallback data redacted', async () => {
    const wrapper = mount(CodingRunTrace, {
      props: {
        runId: 'run-live',
        active: true,
        tools: [{
          id: 'tool-1',
          tool: 'run_shell',
          args: {
            command: "curl -H 'Authorization: Bearer live-secret' https://example.com",
            api_key: 'plain-secret',
          },
          status: 'running',
          result: '',
          is_error: false,
        }],
      },
    })

    expect(wrapper.get('summary').text()).toContain('正在执行')
    expect(wrapper.get('summary').text()).not.toContain('live-secret')
    await wrapper.get('summary').trigger('click')
    expect(wrapper.text()).toContain('[REDACTED]')
    expect(wrapper.text()).not.toContain('plain-secret')
    expect(wrapper.text()).not.toContain('live-secret')
  })

  it('uses a direct waiting headline for an approval without expanding the panel', () => {
    const wrapper = mount(CodingRunTrace, {
      props: { runId: 'run-waiting', tools: [], active: true, pendingTool: 'run_shell' },
    })

    expect(wrapper.get('summary').text()).toContain('等待确认 · run_shell')
    expect(wrapper.get('details').attributes('open')).toBeUndefined()
  })
})
