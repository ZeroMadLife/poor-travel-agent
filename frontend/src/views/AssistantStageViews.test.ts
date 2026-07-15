import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { expect, it } from 'vitest'
import KnowledgeView from './KnowledgeView.vue'

it('shows an honest knowledge phase boundary without fake ingest controls', async () => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/knowledge', component: KnowledgeView },
      { path: '/assistant', component: { template: '<div />' } },
      { path: '/coding', component: { template: '<div />' } },
      { path: '/evolution', component: { template: '<div />' } },
      { path: '/public', component: { template: '<div />' } },
      { path: '/settings/appearance', component: { template: '<div />' } },
    ],
  })
  await router.push('/knowledge')
  const wrapper = mount(KnowledgeView, { global: { plugins: [router] } })

  expect(wrapper.text()).toContain('尚未配置 KnowledgeWorkspace')
  expect(wrapper.text()).toContain('V7-P2')
  expect(wrapper.find('button').exists()).toBe(false)
  wrapper.unmount()
})
