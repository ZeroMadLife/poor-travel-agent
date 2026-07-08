import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import CodingApprovalCard from './CodingApprovalCard.vue'

it('renders approval details and emits allow or deny choices', async () => {
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
  await wrapper.find('button.deny').trigger('click')

  expect(wrapper.emitted('respond')).toEqual([['once'], ['deny']])
})
