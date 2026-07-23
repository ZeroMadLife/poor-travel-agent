import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { expect, it, vi } from 'vitest'
import PublicProfileView from './PublicProfileView.vue'

function mountPublicProfile() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: PublicProfileView }],
  })
  return mount(PublicProfileView, { global: { plugins: [router] } })
}

it('leads with the public product identity and three truthful engineering proofs', () => {
  const wrapper = mountPublicProfile()

  expect(wrapper.get('h1').text()).toContain('ZeroMadLife / Sage')
  expect(wrapper.text()).toContain('Personal AI Learning Companion')
  expect(wrapper.findAll('[data-hero-evidence]')).toHaveLength(3)
  expect(wrapper.text()).toContain('Goal Contract')
  expect(wrapper.text()).toContain('Harness 2.0')
  expect(wrapper.text()).toContain('Mastery Evidence')
  expect(wrapper.text()).not.toContain('掌握率')
  expect(wrapper.text()).not.toContain('%')

  wrapper.unmount()
})

it('labels Ask Sage as a bounded public Agent with transparent fallback', async () => {
  const wrapper = mountPublicProfile()

  await wrapper.get('.ask-sage').trigger('click')

  expect(wrapper.get('.public-agent').attributes('aria-label')).toBe('受限公开资料问答')
  expect(wrapper.text()).toContain('无私人数据')
  expect(wrapper.text()).toContain('失败时透明回退')
  expect(wrapper.text()).toContain('same-origin API')
  expect(wrapper.text()).not.toContain('/Users/')

  wrapper.unmount()
})

it('opens evidence detail without leaving the public surface', async () => {
  const wrapper = mountPublicProfile()
  const mastery = wrapper.get('[data-work-id="mastery"]')

  await mastery.trigger('click')

  expect(mastery.attributes('aria-expanded')).toBe('true')
  expect(wrapper.get('[data-work-evidence="mastery"]').text()).toContain('怎么判断有效')
  expect(wrapper.get('[data-work-evidence="mastery"]').text()).toContain('固定 rubric')

  wrapper.unmount()
})

it('shows a visible public-corpus fallback when the Agent cannot be reached', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('offline') }))
  const wrapper = mountPublicProfile()

  await wrapper.get('.ask-sage').trigger('click')
  await wrapper.get('.agent-prompts button').trigger('click')
  await wrapper.get('.agent-form').trigger('submit')
  await flushPromises()

  expect(wrapper.text()).toContain('公开问答连接失败')
  expect(wrapper.text()).toContain('以下为本页公开资料回退')
  expect(wrapper.text()).not.toContain('资料包 2026-07-22.1')
  wrapper.unmount()
})
