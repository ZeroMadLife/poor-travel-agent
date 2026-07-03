import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from './useAuth'

describe('useAuth', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('verifies a passphrase and stores the returned user id', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ valid: true, user_id: 'u_123' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const auth = useAuth()
    const valid = await auth.verify('tour2026')

    expect(valid).toBe(true)
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/auth'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ passphrase: 'tour2026' }),
      }),
    )
    expect(auth.getUserId()).toBe('u_123')
    expect(auth.isAuthenticated()).toBe(true)
  })

  it('does not store credentials for invalid passphrases', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ valid: false, user_id: '' }),
      }),
    )

    const auth = useAuth()
    const valid = await auth.verify('wrong')

    expect(valid).toBe(false)
    expect(auth.getUserId()).toBe('')
    expect(auth.isAuthenticated()).toBe(false)
  })
})
