import { describe, expect, it } from 'vitest'
import { resolveGithubProof } from './githubMeta'

describe('github meta', () => {
  it('shows star only when count is a positive number', () => {
    expect(resolveGithubProof({
      htmlUrl: 'https://github.com/ZeroMadLife/sage-agent',
      stargazersCount: 12,
      fetchedAt: '2026-07-20T00:00:00Z',
    })).toEqual({
      htmlUrl: 'https://github.com/ZeroMadLife/sage-agent',
      starLabel: '12',
      showStars: true,
    })
  })

  it('degrades gracefully when star is missing', () => {
    expect(resolveGithubProof({
      htmlUrl: 'https://github.com/ZeroMadLife/sage-agent',
      stargazersCount: null,
      fetchedAt: null,
    })).toEqual({
      htmlUrl: 'https://github.com/ZeroMadLife/sage-agent',
      starLabel: null,
      showStars: false,
    })
  })
})
