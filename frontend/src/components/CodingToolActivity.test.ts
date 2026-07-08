import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import CodingToolActivity from './CodingToolActivity.vue'

it('truncates long tool results and can expand them', async () => {
  const longResult = `first sentence. ${'x'.repeat(900)}\n+added\n-removed`
  const wrapper = mount(CodingToolActivity, {
    props: {
      isThinking: true,
      tools: [
        {
          tool: 'patch_file',
          args: { path: 'README.md' },
          status: 'done',
          content: longResult,
        },
      ],
    },
  })

  expect(wrapper.text()).toContain('Show more')
  expect(wrapper.text()).not.toContain('removed')

  await wrapper.find('button.show-more').trigger('click')

  expect(wrapper.text()).toContain('Show less')
  expect(wrapper.text()).toContain('removed')
  expect(wrapper.find('.diff-add').exists()).toBe(true)
  expect(wrapper.find('.diff-remove').exists()).toBe(true)
})
