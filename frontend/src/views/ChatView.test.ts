import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ChatView from './ChatView.vue'

describe('ChatView auth gate', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows passphrase input before authentication', () => {
    const wrapper = mount(ChatView)

    expect(wrapper.text()).toContain('请输入口令进入')
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('试试问我')
  })

  it('shows an error for invalid passphrases', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ valid: false, user_id: '' }),
      }),
    )
    const wrapper = mount(ChatView)

    await wrapper.find('input[type="password"]').setValue('wrong')
    await wrapper.find('button').trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('口令错误')
  })
})
