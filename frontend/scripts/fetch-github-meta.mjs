import { writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(fileURLToPath(import.meta.url))
const out = join(root, '../public-content/github.meta.json')
const api = process.env.SAGE_GITHUB_REPO_API || 'https://api.github.com/repos/ZeroMadLife/sage-agent'

const fallback = {
  htmlUrl: 'https://github.com/ZeroMadLife/sage-agent',
  stargazersCount: null,
  fetchedAt: null,
}

async function main() {
  try {
    const res = await fetch(api, {
      headers: {
        Accept: 'application/vnd.github+json',
        'User-Agent': 'sage-public-build',
        ...(process.env.GITHUB_TOKEN
          ? { Authorization: `Bearer ${process.env.GITHUB_TOKEN}` }
          : {}),
      },
    })
    if (!res.ok) throw new Error(`GitHub API ${res.status}`)
    const data = await res.json()
    writeFileSync(
      out,
      `${JSON.stringify(
        {
          htmlUrl: data.html_url || fallback.htmlUrl,
          stargazersCount: typeof data.stargazers_count === 'number' ? data.stargazers_count : null,
          fetchedAt: new Date().toISOString(),
        },
        null,
        2,
      )}\n`,
    )
  } catch {
    writeFileSync(out, `${JSON.stringify(fallback, null, 2)}\n`)
  }
}

void main()
