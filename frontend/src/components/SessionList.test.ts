import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import SessionList from './SessionList.vue'

it('renders sessions and emits selection events', async () => {
  const wrapper = mount(SessionList, {
    props: {
      sessions: [
        {
          session_id: 's1',
          title: '杭州2日游',
          created_at: '2026-07-03T00:00:00',
          updated_at: '2026-07-03T00:00:00',
          status: 'active',
        },
      ],
      activeSessionId: '',
    },
  })

  expect(wrapper.text()).toContain('历史会话')
  expect(wrapper.text()).toContain('杭州2日游')

  await wrapper.get('button.session-item').trigger('click')
  await wrapper.get('button.new-session').trigger('click')

  expect(wrapper.emitted('select')?.[0]).toEqual(['s1'])
  expect(wrapper.emitted('new')?.length).toBe(1)
})
