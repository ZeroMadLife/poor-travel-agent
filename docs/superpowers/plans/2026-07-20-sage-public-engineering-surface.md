# Sage 公开工程门面 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把独立公开站改造成面试官向的工程落地门面 + 轻量笔记，质感接近 zlog，并保留 Ask Sage 与后续有限权限 harness 接入点。

**Architecture:** 继续使用 `build:public` 独立静态产物与严格 CSP。公开站拆成 Shell / Home sections / Notes / Ask adapter 四组模块；内容与 GitHub meta 走构建期静态数据，不在浏览器请求私人 API 或 GitHub。主应用路由与工作台 UI 本期不动。

**Tech Stack:** Vue 3 + Vue Router + Pinia + Vite public config + Vitest + markdown-it + 现有 lucide icons

**Spec:** `docs/superpowers/specs/2026-07-20-sage-public-engineering-surface-design.md`

**Branch / worktree:**
- 从 `dev/sage-v7` 开独立 worktree
- 分支名建议：`codex/feat-public-engineering-surface`
- 不在仓库根目录直接开发或提交实现代码
- 设计/计划文档若已在根目录产生，实现分支可一并纳入同一 PR 或先单独文档 PR

---

## File map

### Create

| Path | Responsibility |
| --- | --- |
| `frontend/public-content/site.meta.json` | 品牌、仓库、默认文案 meta |
| `frontend/public-content/home.sections.json` | 首页模块文案与证据数据 |
| `frontend/public-content/ask-corpus.json` | Ask Sage 静态语料 |
| `frontend/public-content/github.meta.json` | 构建时写入 star；仓库内提交 fallback 模板 |
| `frontend/public-content/notes/*.md` | 工程笔记 Markdown |
| `frontend/scripts/fetch-github-meta.mjs` | 构建前拉取 GitHub star |
| `frontend/src/public/content.ts` | 读取/解析公开内容与 notes frontmatter |
| `frontend/src/public/content.test.ts` | 内容解析测试 |
| `frontend/src/public/githubMeta.ts` | star 读取与降级 |
| `frontend/src/public/githubMeta.test.ts` | star 降级测试 |
| `frontend/src/components/public/PublicAppShell.vue` | 公开站外壳 |
| `frontend/src/components/public/PublicHeader.vue` | 胶囊导航 + GitHub + Ask |
| `frontend/src/components/public/PublicMobileNav.vue` | 汉堡菜单 |
| `frontend/src/components/public/PublicFooter.vue` | 页脚 |
| `frontend/src/components/public/PublicAskSageDrawer.vue` | Ask Sage 抽屉 |
| `frontend/src/components/public/home/HeroProblem.vue` | Hero |
| `frontend/src/components/public/home/HarnessSystem.vue` | Harness 体系 |
| `frontend/src/components/public/home/EvidenceGallery.vue` | 三截图证据 |
| `frontend/src/components/public/home/GithubProof.vue` | GitHub 证明卡 |
| `frontend/src/components/public/home/NotesPreview.vue` | 首页笔记预览 |
| `frontend/src/components/public/home/GrowthPath.vue` | 成长边界 |
| `frontend/src/components/public/notes/NoteCard.vue` | 笔记卡片 |
| `frontend/src/components/public/notes/MarkdownArticle.vue` | Markdown 渲染 |
| `frontend/src/views/public/PublicHomeView.vue` | 首页组装 |
| `frontend/src/views/public/NotesListView.vue` | `/notes` |
| `frontend/src/views/public/NoteDetailView.vue` | `/notes/:slug` |
| `frontend/src/views/public/PublicHomeView.test.ts` | 首页关键交互 |
| `frontend/src/views/public/NotesViews.test.ts` | 笔记路由 |

### Modify

| Path | Change |
| --- | --- |
| `frontend/src/router/public.ts` | 增加 `/notes`、`/notes/:slug`，首页改 `PublicHomeView` |
| `frontend/src/public-main.ts` | 挂 shell/theme 如需要 |
| `frontend/src/harness/publicAgent.ts` | corpus 外置 + mode 类型预留 limited_harness |
| `frontend/src/harness/publicAgent.test.ts` | 适配新 corpus / mode |
| `frontend/src/views/PublicProfileView.vue` | 收敛为兼容包装或删除后由 home 取代 |
| `frontend/src/views/PublicProfileRouteView.vue` | 主应用 `/#/public` 仍可预览新首页 |
| `frontend/src/views/ProductShellViews.test.ts` | 更新公开站断言，避免绑定旧文案 |
| `frontend/package.json` | `prebuild:public` / `build:public` 接入 github meta 脚本 |
| `frontend/vite.public.config.ts` | alias / raw markdown import 如需要 |
| `docs/runbooks/09-Sage私有Canary部署.md` | 补一句公开站新路由与构建脚本 |

### Keep unchanged

- 主应用 Assistant / Knowledge / Coding / Settings
- `infra/docker/sage-public.Dockerfile` 入口命令（仍 `npm run build:public`）
- v1 CSP `connect-src 'none'`

---

### Task 0: Worktree 与基线

**Files:**
- None in product code

- [ ] **Step 1: 从 `dev/sage-v7` 创建 worktree**

```bash
git fetch origin
git worktree add ../sage-public-engineering-surface -b codex/feat-public-engineering-surface dev/sage-v7
cd ../sage-public-engineering-surface
```

Expected: 新 worktree 位于干净分支。

- [ ] **Step 2: 确认前端可测**

```bash
cd frontend
npm ci
npm run test -- --run src/harness/publicAgent.test.ts src/views/ProductShellViews.test.ts
```

Expected: PASS（作为改造前基线）。

- [ ] **Step 3: 若设计/计划文档不在该分支，复制或 cherry-pick 文档提交**

确保以下文件存在：

- `docs/superpowers/specs/2026-07-20-sage-public-engineering-surface-design.md`
- `docs/superpowers/plans/2026-07-20-sage-public-engineering-surface.md`

- [ ] **Step 4: Commit docs if needed**

```bash
git add docs/superpowers/specs/2026-07-20-sage-public-engineering-surface-design.md \
  docs/superpowers/plans/2026-07-20-sage-public-engineering-surface.md
git commit -m "$(cat <<'EOF'
docs(public): 公开工程门面设计与实现计划

EOF
)"
```

---

### Task 1: 公开内容模型与 GitHub meta 降级

**Files:**
- Create: `frontend/public-content/site.meta.json`
- Create: `frontend/public-content/home.sections.json`
- Create: `frontend/public-content/ask-corpus.json`
- Create: `frontend/public-content/github.meta.json`
- Create: `frontend/src/public/content.ts`
- Create: `frontend/src/public/content.test.ts`
- Create: `frontend/src/public/githubMeta.ts`
- Create: `frontend/src/public/githubMeta.test.ts`
- Create: `frontend/scripts/fetch-github-meta.mjs`
- Modify: `frontend/package.json`

- [ ] **Step 1: 写失败测试 — content 与 github meta**

`frontend/src/public/content.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { listNotes, parseNoteMarkdown, getSiteMeta } from './content'

describe('public content', () => {
  it('reads site meta repository url', () => {
    expect(getSiteMeta().githubRepoUrl).toContain('ZeroMadLife/sage-agent')
  })

  it('parses note frontmatter without executing html', () => {
    const note = parseNoteMarkdown(`---
title: 测试笔记
date: 2026-07-20
summary: 摘要
tags: [harness]
---

## 标题

正文 <script>alert(1)</script>
`)
    expect(note.slug).toBeTruthy()
    expect(note.title).toBe('测试笔记')
    expect(note.tags).toEqual(['harness'])
    expect(note.body).toContain('正文')
    expect(note.body).toContain('<script>alert(1)</script>')
  })
})
```

`frontend/src/public/githubMeta.test.ts`:

```ts
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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd frontend
npm run test -- --run src/public/content.test.ts src/public/githubMeta.test.ts
```

Expected: FAIL，模块不存在。

- [ ] **Step 3: 落地最小内容文件与模块**

`frontend/public-content/site.meta.json`:

```json
{
  "brand": "ZeroMadLife / Sage",
  "title": "ZeroMadLife / Sage",
  "description": "面试官向的公开工程现场：可恢复 Agent Harness、真实工作台证据与工程笔记。",
  "githubRepoUrl": "https://github.com/ZeroMadLife/sage-agent",
  "githubRepoApi": "https://api.github.com/repos/ZeroMadLife/sage-agent"
}
```

`frontend/public-content/github.meta.json`（fallback，构建可覆盖）:

```json
{
  "htmlUrl": "https://github.com/ZeroMadLife/sage-agent",
  "stargazersCount": null,
  "fetchedAt": null
}
```

`frontend/public-content/home.sections.json` 最小字段：

```json
{
  "hero": {
    "eyebrow": "ENGINEERING SURFACE",
    "title": "不是又一个聊天框。是可恢复的学习运行时。",
    "lede": "Sage 用 Harness 把目标、知识、实践和证据串成一条可审计路径。这里展示工程落地，不是包装好的 demo。",
    "primaryCta": "看 Harness 体系",
    "secondaryCta": "GitHub 源码"
  },
  "harness": {
    "eyebrow": "01 / HARNESS",
    "title": "同一条运行时，服务多个工作面",
    "items": [
      { "id": "plan", "title": "Plan", "detail": "目标拆解" },
      { "id": "tool", "title": "Tool", "detail": "受控执行" },
      { "id": "approve", "title": "Approve", "detail": "危险操作确认" },
      { "id": "evidence", "title": "Evidence", "detail": "可回放结果" }
    ]
  },
  "evidence": {
    "eyebrow": "02 / EVIDENCE",
    "title": "真实工作台，不是概念图",
    "items": [
      { "id": "assistant", "title": "Assistant", "caption": "目标驱动入口" },
      { "id": "knowledge", "title": "Knowledge", "caption": "图谱与引用治理" },
      { "id": "practice", "title": "Practice", "caption": "受控执行与证据" }
    ]
  },
  "path": {
    "eyebrow": "03 / PATH",
    "title": "成长与边界",
    "items": [
      { "date": "2026 · 07", "title": "Reliable Agent Harness", "detail": "恢复、审批、持久 Timeline 进入同一运行路径。", "state": "now" },
      { "date": "2026 · 06", "title": "Personal Knowledge Base", "detail": "来源、Wiki、检索与 revision 形成可追溯结构。", "state": "done" }
    ]
  }
}
```

`frontend/public-content/ask-corpus.json`：把现有 `publicAgent.ts` entries 搬出，结构：

```json
{
  "entries": [
    {
      "keywords": ["sage", "做什么", "项目", "学习助手"],
      "answer": "Sage 是一个 Personal AI Learning Companion：用户先设定目标，再让主对话结合个人知识和外部证据，安排练习并记录可验证进步。",
      "sources": [
        { "id": "sage", "label": "Sage 项目现场", "target": "work", "detail": "目标、Knowledge、Practice 与 Evidence 的产品闭环" }
      ]
    }
  ],
  "fallback": "这版问答只覆盖已经公开的 Sage、Harness、Knowledge 和成长记录。私有工作区、Session、Memory 与未发布资料不会进入这个公开入口。"
}
```

实现 `content.ts` / `githubMeta.ts`：

- `getSiteMeta()` 读 `site.meta.json`
- `parseNoteMarkdown(raw, slug?)` 解析 YAML frontmatter（可用极简手写 parser，不要引入新依赖）
- `listNotes()` 先返回静态 import 列表（Task 3 接 notes 文件）
- `resolveGithubProof(meta)` 仅当 `stargazersCount` 为有限数字且 `> 0` 时 `showStars=true`

`frontend/scripts/fetch-github-meta.mjs`:

```js
import { writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

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
        ...(process.env.GITHUB_TOKEN ? { Authorization: `Bearer ${process.env.GITHUB_TOKEN}` } : {}),
      },
    })
    if (!res.ok) throw new Error(`GitHub API ${res.status}`)
    const data = await res.json()
    writeFileSync(out, JSON.stringify({
      htmlUrl: data.html_url || fallback.htmlUrl,
      stargazersCount: typeof data.stargazers_count === 'number' ? data.stargazers_count : null,
      fetchedAt: new Date().toISOString(),
    }, null, 2) + '\n')
  } catch {
    writeFileSync(out, JSON.stringify(fallback, null, 2) + '\n')
  }
}

main()
```

`package.json` scripts:

```json
{
  "fetch:github-meta": "node ./scripts/fetch-github-meta.mjs",
  "build:public": "npm run fetch:github-meta && vue-tsc -b && vite build --config vite.public.config.ts"
}
```

- [ ] **Step 4: 跑测试通过**

```bash
cd frontend
npm run test -- --run src/public/content.test.ts src/public/githubMeta.test.ts
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/public-content frontend/src/public frontend/scripts/fetch-github-meta.mjs frontend/package.json
git commit -m "$(cat <<'EOF'
feat(public): 增加公开内容模型与 GitHub star 构建注入

EOF
)"
```

---

### Task 2: publicAgent corpus 外置 + limited_harness 模式预留

**Files:**
- Modify: `frontend/src/harness/publicAgent.ts`
- Modify: `frontend/src/harness/publicAgent.test.ts`
- Modify: `frontend/public-content/ask-corpus.json`（补齐 harness/knowledge/growth 条目）

- [ ] **Step 1: 更新测试**

保留现有两个用例，并追加：

```ts
it('exposes static mode and never invents limited harness answers without flag', async () => {
  const response = await answerPublicProfileQuestion('Harness 2.0 如何恢复运行？')
  expect(response.mode).toBe('static')
  expect(response.mode).not.toBe('limited_harness')
})
```

- [ ] **Step 2: 运行确认当前实现仍过或需改**

```bash
cd frontend
npm run test -- --run src/harness/publicAgent.test.ts
```

- [ ] **Step 3: 改 `publicAgent.ts`**

关键形状：

```ts
export type PublicAgentMode = 'static' | 'limited_harness'

export type PublicAgentResponse = {
  mode: PublicAgentMode
  answer: string
  sources: PublicAgentSource[]
}

// v1: always static matcher over ask-corpus.json
// v2 later: if import.meta.env.VITE_PUBLIC_AGENT_MODE === 'limited_harness' then remote public API
export async function answerPublicProfileQuestion(question: string): Promise<PublicAgentResponse> {
  // load corpus, score keywords, return fallback when no match
}
```

要求：

- 不在 v1 发起任何 `fetch`
- 不读取私人路径
- fallback 文案继续强调公开边界

- [ ] **Step 4: 测试通过**

```bash
cd frontend
npm run test -- --run src/harness/publicAgent.test.ts
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/harness/publicAgent.ts frontend/src/harness/publicAgent.test.ts frontend/public-content/ask-corpus.json
git commit -m "$(cat <<'EOF'
feat(public): 外置 Ask Sage 语料并预留 limited harness 模式

EOF
)"
```

---

### Task 3: 公开站 Shell + 路由

**Files:**
- Create: `frontend/src/components/public/PublicAppShell.vue`
- Create: `frontend/src/components/public/PublicHeader.vue`
- Create: `frontend/src/components/public/PublicMobileNav.vue`
- Create: `frontend/src/components/public/PublicFooter.vue`
- Create: `frontend/src/views/public/PublicHomeView.vue`（先可放占位 section，Task 4 填满）
- Create: `frontend/src/views/public/PublicHomeView.test.ts`
- Modify: `frontend/src/router/public.ts`
- Modify: `frontend/src/public-main.ts`（如需）
- Modify: `frontend/src/views/PublicProfileRouteView.vue`

- [ ] **Step 1: 写 shell 测试**

`PublicHomeView.test.ts` 先验证导航骨架：

```ts
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { expect, it } from 'vitest'
import PublicHomeView from './PublicHomeView.vue'
import PublicAppShell from '../../components/public/PublicAppShell.vue'

it('renders capsule navigation and github proof entry', async () => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: PublicHomeView }],
  })
  await router.push('/')
  const wrapper = mount(PublicAppShell, {
    global: { plugins: [router] },
    slots: { default: PublicHomeView },
  })
  expect(wrapper.text()).toContain('ZeroMadLife')
  expect(wrapper.text()).toMatch(/GitHub/)
  expect(wrapper.find('[data-nav="notes"]').exists() || wrapper.text().includes('笔记')).toBe(true)
  wrapper.unmount()
})
```

- [ ] **Step 2: 跑测试失败**

```bash
cd frontend
npm run test -- --run src/views/public/PublicHomeView.test.ts
```

- [ ] **Step 3: 实现 shell 组件与 public router**

`frontend/src/router/public.ts`:

```ts
import { createRouter, createWebHistory } from 'vue-router'
import PublicHomeView from '../views/public/PublicHomeView.vue'
import NotesListView from '../views/public/NotesListView.vue'
import NoteDetailView from '../views/public/NoteDetailView.vue'

const publicRouter = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'public.home', component: PublicHomeView },
    { path: '/notes', name: 'public.notes', component: NotesListView },
    { path: '/notes/:slug', name: 'public.note', component: NoteDetailView, props: true },
    { path: '/public', redirect: '/' },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior(to) {
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    return { top: 0 }
  },
})

export default publicRouter
```

`PublicHeader.vue` 要求：

- 桌面胶囊：`首页 / 体系 / 证据 / 笔记 / 关于`
- 体系/证据/关于：首页锚点 `#harness` `#evidence` `#about`
- 笔记：`router-link` 到 `/notes`
- 右侧：GitHub（含可选 star）+ `问 Sage` 按钮 emit
- `< md`：隐藏胶囊，显示汉堡

`PublicAppShell.vue`：

- 持有 `askOpen` 状态
- 渲染 header / main slot / footer / Ask drawer 占位

`PublicHomeView.vue` 先输出带 id 的 section 壳：

```vue
<section id="top" />
<section id="harness" />
<section id="evidence" />
<section id="notes" />
<section id="path" />
<section id="about" />
```

`NotesListView` / `NoteDetailView` 可先最小实现，Task 5 补正文。

主应用兼容：

- `PublicProfileRouteView` 继续在 draft preview 时用 `PublicDraftPreview`
- 否则渲染 `PublicHomeView` 或薄包装，保证 `/#/public` 不白屏

- [ ] **Step 4: 测试通过**

```bash
cd frontend
npm run test -- --run src/views/public/PublicHomeView.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/public frontend/src/views/public frontend/src/router/public.ts frontend/src/views/PublicProfileRouteView.vue frontend/src/public-main.ts
git commit -m "$(cat <<'EOF'
feat(public): 增加公开站 shell 与 notes 路由骨架

EOF
)"
```

---

### Task 4: 首页工程叙事模块

**Files:**
- Create/Modify: `frontend/src/components/public/home/*.vue`
- Modify: `frontend/src/views/public/PublicHomeView.vue`
- Modify: `frontend/src/views/public/PublicHomeView.test.ts`
- Modify: `frontend/src/views/ProductShellViews.test.ts`
- Assets: 复用 `frontend/src/assets/public/sage-knowledge-workbench.jpg` 与 README 截图导出到 public 资产（若需复制，放 `frontend/src/assets/public/`）

- [ ] **Step 1: 扩展首页测试**

```ts
it('leads with problem narrative and harness evidence, not a blog diary', async () => {
  // mount PublicHomeView with router
  expect(wrapper.text()).toContain('不是又一个聊天框')
  expect(wrapper.text()).toContain('HARNESS')
  expect(wrapper.text()).toContain('Timeline') // or Plan/Tool/Approve/Evidence
  expect(wrapper.text()).toContain('真实工作台')
  expect(wrapper.text()).toMatch(/GitHub/)
})
```

同步更新 `ProductShellViews.test.ts`：

- 不再依赖旧文案 `只回答这页已经公开的项目、方法和成长记录` 的精确句子，可改为包含 `公开资料预览`
- 导航 section 从 `writing` 调整为新 `data-section`（如 `notes` / `evidence`）
- work evidence 折叠若首页不再保留，删除对应用例或改成 harness/evidence 断言

- [ ] **Step 2: 跑测试失败**

```bash
cd frontend
npm run test -- --run src/views/public/PublicHomeView.test.ts src/views/ProductShellViews.test.ts
```

- [ ] **Step 3: 实现首页 sections**

组装顺序必须是：

1. `HeroProblem`
2. `HarnessSystem`
3. `EvidenceGallery`
4. `GithubProof`
5. `NotesPreview`
6. `GrowthPath`
7. about 简段（可放 `PublicHomeView` 内）

视觉要求：

- 胶囊导航 + 更密卡片
- Sage 绿主色
- 支持 `data-theme` light/dark（可复用根 token 或 public 局部 token）
- 移动端无横向溢出

Ask Sage：

- Header 按钮打开 drawer
- Hero 次 CTA 不取代“看源码”，可另给“向公开资料提问”

- [ ] **Step 4: 测试通过**

```bash
cd frontend
npm run test -- --run src/views/public/PublicHomeView.test.ts src/views/ProductShellViews.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/public/home frontend/src/views/public/PublicHomeView.vue \
  frontend/src/views/public/PublicHomeView.test.ts frontend/src/views/ProductShellViews.test.ts \
  frontend/src/assets/public
git commit -m "$(cat <<'EOF'
feat(public): 重排首页为 Harness 工程落地叙事

EOF
)"
```

---

### Task 5: 轻量笔记列表与详情

**Files:**
- Create: `frontend/public-content/notes/why-durable-timeline.md`
- Create: `frontend/public-content/notes/approval-is-not-decoration.md`
- Create: `frontend/public-content/notes/public-csp-boundary.md`（可选第 3 篇）
- Create: `frontend/src/components/public/notes/NoteCard.vue`
- Create: `frontend/src/components/public/notes/MarkdownArticle.vue`
- Modify: `frontend/src/views/public/NotesListView.vue`
- Modify: `frontend/src/views/public/NoteDetailView.vue`
- Create: `frontend/src/views/public/NotesViews.test.ts`
- Modify: `frontend/src/public/content.ts`（listNotes 接真实文件）
- Modify: `frontend/vite.public.config.ts`（如需 `?raw` alias）

- [ ] **Step 1: 写笔记测试**

```ts
it('lists engineering notes and opens a markdown detail page', async () => {
  // router with /notes and /notes/:slug
  await router.push('/notes')
  expect(wrapper.text()).toContain('工程笔记')
  expect(wrapper.text()).toContain('durable timeline') // 或中文标题
  await router.push('/notes/why-durable-timeline')
  expect(wrapper.text()).toContain('为什么')
  expect(wrapper.html()).not.toContain('<script>alert')
})
```

- [ ] **Step 2: 跑测试失败**

```bash
cd frontend
npm run test -- --run src/views/public/NotesViews.test.ts
```

- [ ] **Step 3: 实现笔记内容与页面**

笔记主题固定工程向，例如：

1. 为什么 Harness 需要 durable timeline
2. 审批点不是 UI 装饰
3. 公开站为何保持 `connect-src none`

`MarkdownArticle` 复用 `useMarkdown()`（`html: false` 已存在）。

`listNotes()`：

- 使用 Vite `import.meta.glob('../../public-content/notes/*.md', { eager: true, query: '?raw', import: 'default' })`
- 或在 `content.ts` 中静态登记 2–3 个 raw import

详情页 404 slug：回退到 `/notes`。

首页 `NotesPreview` 取最近 2–3 篇。

- [ ] **Step 4: 测试通过**

```bash
cd frontend
npm run test -- --run src/views/public/NotesViews.test.ts src/public/content.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add frontend/public-content/notes frontend/src/components/public/notes \
  frontend/src/views/public/NotesListView.vue frontend/src/views/public/NoteDetailView.vue \
  frontend/src/views/public/NotesViews.test.ts frontend/src/public/content.ts frontend/vite.public.config.ts
git commit -m "$(cat <<'EOF'
feat(public): 增加静态工程笔记列表与详情页

EOF
)"
```

---

### Task 6: Ask Sage 抽屉组件化

**Files:**
- Create: `frontend/src/components/public/PublicAskSageDrawer.vue`
- Modify: `frontend/src/components/public/PublicAppShell.vue`
- Modify: `frontend/src/views/public/PublicHomeView.test.ts`
- Modify: `frontend/src/views/ProductShellViews.test.ts`

- [ ] **Step 1: 写/更新 Ask Sage 测试**

```ts
it('opens Ask Sage as secondary public-preview chat with source receipts', async () => {
  await wrapper.get('[data-action="ask-sage"]').trigger('click')
  expect(wrapper.text()).toContain('公开资料预览')
  // submit a prompt
  expect(wrapper.text()).toContain('回答依据')
  expect(wrapper.text()).not.toContain('/Users/')
})
```

- [ ] **Step 2: 跑测试**

```bash
cd frontend
npm run test -- --run src/views/public/PublicHomeView.test.ts src/views/ProductShellViews.test.ts
```

- [ ] **Step 3: 抽出抽屉并接线**

从旧 `PublicProfileView.vue` 迁移：

- 消息流
- sources 按钮
- 预设问题
- disclaimer：“当前是静态资料问答，后续可替换为受限公网 Harness。”

sources 点击：

- `work/harness/evidence` → 回首页锚点
- 未来可扩到 notes slug

- [ ] **Step 4: 删除或收敛旧 `PublicProfileView.vue` 大段重复 UI**

可选策略：

- A. `PublicProfileView.vue` 变为 `PublicHomeView` 的 re-export / 薄包装，减少主应用引用破裂
- B. 全量替换引用后删除旧文件

优先 A，改动面更小。

- [ ] **Step 5: 测试通过并 commit**

```bash
cd frontend
npm run test -- --run src/views/public/PublicHomeView.test.ts src/views/ProductShellViews.test.ts src/harness/publicAgent.test.ts

git add frontend/src/components/public/PublicAskSageDrawer.vue frontend/src/components/public/PublicAppShell.vue \
  frontend/src/views/PublicProfileView.vue frontend/src/views/public frontend/src/views/ProductShellViews.test.ts
git commit -m "$(cat <<'EOF'
feat(public): 组件化 Ask Sage 并保持公开资料边界

EOF
)"
```

---

### Task 7: 视觉 polish、主题与移动端验收点

**Files:**
- Modify: public shell/home/notes 样式
- Optional: `frontend/src/style.css` 仅增加 public 不冲突 token
- Modify tests if aria labels change

- [ ] **Step 1: 手工/测试清单固化到测试能覆盖的部分**

至少自动覆盖：

- header 存在 mobile menu button：`aria-label="打开导航菜单"`
- `/notes` link 可点
- GitHub anchor `target="_blank"` + `rel` 含 `noreferrer`

- [ ] **Step 2: 实现样式目标**

对照 spec：

- 胶囊导航 active 态
- 卡片密度高于旧 public 页
- light/dark 切换（可用 localStorage key `sage-public-theme`）
- `prefers-reduced-motion` 禁用非必要 transition
- 560px / 390px 宽度无横向滚动

- [ ] **Step 3: 跑相关测试**

```bash
cd frontend
npm run test -- --run src/views/public src/public src/harness/publicAgent.test.ts src/views/ProductShellViews.test.ts
```

- [ ] **Step 4: Commit**

```bash
git commit -am "$(cat <<'EOF'
style(public): 提升公开站密度、导航与主题质感

EOF
)"
```

---

### Task 8: build:public 门禁与部署说明

**Files:**
- Modify: `frontend/package.json`（若还需 `check:public-bundle` 脚本）
- Create optional: `frontend/scripts/check-public-bundle.mjs`
- Modify: `docs/runbooks/09-Sage私有Canary部署.md`

- [ ] **Step 1: 增加产物扫描脚本（推荐）**

`frontend/scripts/check-public-bundle.mjs`：

- 读取 `dist-public/assets/*.js`
- 若包含 `"/assistant"`、`"/coding/session"`、`"/settings/"` 等私有路由字符串则失败
- 允许 `github.com` 与公开文案

`package.json`:

```json
{
  "check:public-bundle": "node ./scripts/check-public-bundle.mjs",
  "build:public": "npm run fetch:github-meta && vue-tsc -b && vite build --config vite.public.config.ts && npm run check:public-bundle"
}
```

- [ ] **Step 2: 执行生产公开构建**

```bash
cd frontend
npm run build:public
```

Expected:

- `dist-public/` 生成
- github meta 写入成功或降级
- bundle check PASS

- [ ] **Step 3: 本地 preview**

```bash
cd frontend
npm run preview:public -- --host 127.0.0.1 --port 4173
```

手工打开：

- `/`
- `/notes`
- 任一 note 详情
- Ask Sage
- 缩到 390 宽

- [ ] **Step 4: 更新 runbook 一句**

在 `docs/runbooks/09-Sage私有Canary部署.md` 公开站段落补充：

- 公开站现含 `/`、`/notes`、`/notes/:slug`
- 构建会尝试写入 GitHub star 静态 meta
- v1 仍无后端依赖；limited harness 未启用

- [ ] **Step 5: 全量前端测试 + commit**

```bash
cd frontend
npm run test -- --run
npm run build:public

git add frontend/package.json frontend/scripts docs/runbooks/09-Sage私有Canary部署.md frontend/dist-public 2>/dev/null || true
# 不要提交 dist-public；确认 .gitignore 已忽略
git status
git commit -m "$(cat <<'EOF'
chore(public): 增加公开产物门禁与部署说明

EOF
)"
```

---

### Task 9: PR 收口

- [ ] **Step 1: 验证清单**

```bash
cd frontend
npm run test -- --run
npm run build:public
cd ..
git diff --check
```

- [ ] **Step 2: 写中文 PR**

标题：

`feat(public): 公开工程门面与轻量笔记`

正文至少包含：

- 需求完成度：首页叙事 / notes / Ask Sage / GitHub star / CSP
- 验证证据：测试命令与 build:public
- 未完成边界：HTTPS 域名、limited harness API、Publishing 发布链路、主应用 UI
- 部署建议：先本地 preview，再更新 `sage-public` 镜像

- [ ] **Step 3: 推送并开 PR 到 `dev/sage-v7`**

```bash
git push -u origin codex/feat-public-engineering-surface
gh pr create --base dev/sage-v7 --title "feat(public): 公开工程门面与轻量笔记" --body "$(cat <<'EOF'
## 摘要
- 公开站改为面试官向工程落地门面
- 增加 /notes 轻量笔记
- 保留 Ask Sage，预留 limited harness
- 构建时注入 GitHub star，保持 CSP

## 验证
- `cd frontend && npm run test -- --run`
- `cd frontend && npm run build:public`
- `git diff --check`

## 边界
- 主应用未改
- 未接 public harness API
- HTTPS 域名后续处理
EOF
)"
```

---

## Spec coverage checklist

| Spec 要求 | Task |
| --- | --- |
| 面试官向工程落地叙事 | Task 4 |
| Harness 作为核心证据 | Task 4 |
| 真实工作台证据区 | Task 4 |
| zlog 风格导航/密度/主题 | Task 3, 7 |
| `/notes` + detail | Task 5 |
| GitHub + star 构建注入 | Task 1, 8 |
| Ask Sage 保留 + adapter 预留 | Task 2, 6 |
| `build:public` 与 CSP 边界 | Task 8 |
| 主应用不动 | 全任务约束 |
| worktree + codex 分支 | Task 0, 9 |

## Placeholder scan

本计划不包含 TBD/TODO 实现空步；v2 limited harness 仅预留 mode 与文案，不实现远程 API。

## Type / API consistency

- `answerPublicProfileQuestion(question: string): Promise<PublicAgentResponse>`
- `PublicAgentMode = 'static' | 'limited_harness'`
- `resolveGithubProof(meta) -> { htmlUrl, starLabel, showStars }`
- notes frontmatter: `title`, `date`, `summary`, `tags`, `related?`

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-20-sage-public-engineering-surface.md`.

实现时建议：

1. **Subagent-Driven（推荐）** — 每个 Task 派一个新 subagent，任务间人工/主代理审查  
2. **Inline Execution** — 本会话按 executing-plans 连续推进并设检查点  

无论哪种，先用 `using-git-worktrees` 建 `codex/feat-public-engineering-surface`，不要在仓库根直接改实现。
