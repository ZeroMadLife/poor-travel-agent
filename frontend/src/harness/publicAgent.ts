import { getAskCorpus } from '../public/content'

export type PublicAgentSource = {
  id: string
  label: string
  target: string
  detail: string
}

export type PublicAgentMode = 'static' | 'limited_harness'

export type PublicAgentResponse = {
  mode: PublicAgentMode
  answer: string
  sources: PublicAgentSource[]
}

export async function answerPublicProfileQuestion(question: string): Promise<PublicAgentResponse> {
  // v1 always stays static. limited_harness is reserved for a future public-only API.
  const mode: PublicAgentMode = 'static'
  const corpus = getAskCorpus()
  const normalized = question.trim().toLocaleLowerCase()
  const match = corpus.entries
    .map((entry) => ({
      entry,
      score: entry.keywords.reduce(
        (total, keyword) => total + (normalized.includes(keyword.toLocaleLowerCase()) ? 1 : 0),
        0,
      ),
    }))
    .filter((candidate) => candidate.score > 0)
    .sort((left, right) => right.score - left.score)[0]?.entry

  if (!match) {
    return {
      mode,
      answer: corpus.fallback,
      sources: [],
    }
  }

  return {
    mode,
    answer: match.answer,
    sources: match.sources,
  }
}
