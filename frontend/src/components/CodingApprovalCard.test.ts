import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import CodingApprovalCard from './CodingApprovalCard.vue'

it('renders approval details and emits all approval choices', async () => {
  const wrapper = mount(CodingApprovalCard, {
    props: {
      approval: {
        approval_id: 'appr_1',
        session_id: 'c1',
        tool: 'write_file',
        args: { path: 'README.md' },
        description: 'write_file requires approval.',
        pattern_key: 'tool:write_file',
      },
    },
  })

  expect(wrapper.text()).toContain('write_file')
  expect(wrapper.text()).toContain('write_file requires approval.')

  await wrapper.find('button.allow').trigger('click')
  await wrapper.find('button.session').trigger('click')
  await wrapper.find('button.always').trigger('click')
  await wrapper.find('button.deny').trigger('click')

  expect(wrapper.emitted('respond')).toEqual([['once'], ['session'], ['always'], ['deny']])
})

it('renders diff preview when provided', () => {
  const wrapper = mount(CodingApprovalCard, {
    props: {
      approval: {
        approval_id: 'appr_1',
        session_id: 'c1',
        tool: 'patch_file',
        args: { path: 'README.md' },
        description: 'patch_file requires approval.',
        pattern_key: 'tool:patch_file',
        diff_preview: [
          { type: 'remove', text: 'old title' },
          { type: 'add', text: 'new title' },
        ],
      },
    },
  })

  expect(wrapper.text()).toContain('old title')
  expect(wrapper.text()).toContain('new title')
  expect(wrapper.find('.diff-remove').exists()).toBe(true)
  expect(wrapper.find('.diff-add').exists()).toBe(true)
})
