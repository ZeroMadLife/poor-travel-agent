import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true,
})

// 外部链接加 target=_blank 和 rel=noopener
const defaultRender =
  md.renderer.rules.link_open ||
  function (tokens: { length: number }, idx: number, options: object, _env: unknown, self: unknown) {
    return (self as { renderToken: (t: unknown[], i: number, o: object) => string }).renderToken(tokens, idx, options)
  }

md.renderer.rules.link_open = function (tokens, idx, options, env, self) {
  const targetIndex = tokens[idx].attrIndex('target')
  if (targetIndex < 0) {
    tokens[idx].attrPush(['target', '_blank'])
    tokens[idx].attrPush(['rel', 'noopener noreferrer'])
  } else {
    tokens[idx].attrs![targetIndex][1] = '_blank'
  }
  return defaultRender(tokens, idx, options, env, self)
}

export function useMarkdown() {
  function render(content: string): string {
    if (!content) return ''
    return md.render(content)
  }

  return { render }
}
