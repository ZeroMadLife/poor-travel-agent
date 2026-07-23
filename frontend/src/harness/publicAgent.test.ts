import { afterEach, describe, expect, it, vi } from 'vitest'
import { answerPublicProfileQuestion } from './publicAgent'

afterEach(() => vi.useRealTimers())

describe('public Agent client', () => {
  it('returns live citations and an immutable package receipt', async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({
      status: 'answered',
      answer: 'Harness 从 timeline 恢复。[E1]',
      citations: [{
        citation_id: 'E1', document_id: 'harness-2', title: 'Harness 2.0',
        url: 'https://sagecompanion.top/#harness', revision: 'r2', excerpt: '公开摘要',
      }],
      receipt: { request_id: 'pub_123', package_revision: '2026-07-22.1', package_digest: 'abc' },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))

    const result = await answerPublicProfileQuestion('Harness 如何恢复？', { fetcher })

    expect(result.mode).toBe('live')
    expect(result.receipt?.packageRevision).toBe('2026-07-22.1')
    expect(result.sources[0]).toMatchObject({ id: 'harness-2', revision: 'r2' })
    expect(fetcher).toHaveBeenCalledWith('/api/public/v1/ask', expect.objectContaining({
      method: 'POST', credentials: 'omit', cache: 'no-store',
    }))
  })

  it('makes rate limiting visible and falls back to bounded public copy', async () => {
    const fetcher = vi.fn(async () => new Response('{"detail":"limited"}', {
      status: 429, headers: { 'Retry-After': '60' },
    }))

    const result = await answerPublicProfileQuestion('Sage 是做什么的？', { fetcher })

    expect(result.mode).toBe('fallback')
    expect(result.notice).toContain('60 秒后重试')
    expect(result.answer).toContain('Personal AI Learning Companion')
  })

  it('falls back without fabricating a live receipt when the API is unreachable', async () => {
    const fetcher = vi.fn(async () => { throw new TypeError('network failed') })

    const result = await answerPublicProfileQuestion('Knowledge 是什么？', { fetcher })

    expect(result.mode).toBe('fallback')
    expect(result.notice).toBe('公开问答连接失败')
    expect(result.receipt).toBeUndefined()
  })
})
