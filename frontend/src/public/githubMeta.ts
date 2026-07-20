import githubMetaJson from '../../public-content/github.meta.json'
import { getSiteMeta } from './content'

export type GithubMeta = {
  htmlUrl: string
  stargazersCount: number | null
  fetchedAt: string | null
}

export type GithubProof = {
  htmlUrl: string
  starLabel: string | null
  showStars: boolean
}

export function getGithubMeta(): GithubMeta {
  return githubMetaJson as GithubMeta
}

export function resolveGithubProof(meta: GithubMeta = getGithubMeta()): GithubProof {
  const fallbackUrl = getSiteMeta().githubRepoUrl
  const htmlUrl = meta.htmlUrl || fallbackUrl
  const count = meta.stargazersCount
  const showStars = typeof count === 'number' && Number.isFinite(count) && count > 0
  return {
    htmlUrl,
    starLabel: showStars ? String(count) : null,
    showStars,
  }
}
