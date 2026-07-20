# Sage 公开工程门面设计

日期：2026-07-20  
状态：已评审待实现  
范围：公开站（`build:public` / `sage-public`）  
不在范围：主应用 Assistant / Knowledge / Practice / Settings 改造

## 1. 背景与问题

当前线上公开面 `http://121.40.185.188/` 已是独立静态公开站，而不是主应用私有路由：

- 入口：`frontend/src/public-main.ts` + `vite.public.config.ts`
- 页面：`PublicProfileView.vue` 单文件承载几乎全部公开 UI
- 安全：`connect-src 'none'`，不依赖 API / DB / Redis
- 能力：项目介绍、field notes、成长轨迹、静态 Ask Sage

但它离“可给面试官看的工程落地门面”还有明显差距：

1. **叙事偏素**：像简介页，不像可验证的工程现场。
2. **证据不足**：截图重复、Harness 体系没有成为主证据。
3. **内容系统弱**：笔记硬编码；Publishing Studio 发布按钮仍禁用。
4. **社交证明缺失**：GitHub 链接弱，无 star 等可扫读信任信号。
5. **质感不够**：对比 [zlog](https://zlog-omega.vercel.app/) 缺胶囊导航、移动汉堡、内容密度和站点级 polish。
6. **域名信任未完成**：meta 指向 `sagecompanion.cn`，HTTPS 尚未稳定接通。

主应用前端另有结构性问题（巨型单文件、重复 `* 2.vue`、空态不一致等），**本期明确不改**。公开站先独立达到可展示水平。

## 2. 目标与非目标

### 目标

把公开站做成：

> **面试官向的开源项目落地页 + 轻量工程笔记**

在 60 秒内讲清：

1. Sage 解决什么问题；
2. 为什么不是普通聊天机器人 / demo；
3. Harness 体系如何保证可恢复、可审批、可审计；
4. 有哪些真实工作台证据与源码可追溯路径。

同时补齐接近 zlog 的站点质感：胶囊导航、移动导航、笔记列表/详情、GitHub 证明。

### 成功标准

- 面试官不需要进私有应用，也能判断“这是工程落地，不是包装 demo”。
- 公开站视觉密度与导航完成度接近 zlog，但叙事仍是工程现场，不是生活博客。
- `/notes` 至少有 2 篇可打开的工程笔记。
- GitHub 仓库链接可见；star 有则显示，无则优雅降级。
- `build:public` 仍是纯静态产物，v1 保持严格 CSP。
- Ask Sage 保留，并预留后续有限权限 public harness 接入。

### 非目标

- 不改造主应用工作台 UI。
- 不做完整博客 CMS（标签体系、搜索、评论、账号）。
- 不接通 Publishing Studio 后端发布 API。
- 不在浏览器运行时请求 GitHub API。
- 不在本期上线完整公网 Harness；只做 adapter 预留。
- 不在仓库根目录直接开发；实现走独立 worktree + `codex/*` 分支。

## 3. 用户与 60 秒路径

### 主访客

技术面试官 / 招聘方。

### 次访客

开源浏览者、潜在贡献者。

### 60 秒路径

1. Hero：问题叙事——不是聊天框，是可恢复学习运行时。
2. Harness 体系：Timeline / Approval / Recovery / Surfaces。
3. 真实证据：Assistant / Knowledge / Practice 截图与路径说明。
4. 信任与延伸：GitHub + star、工程笔记、成长边界。

## 4. 信息架构与路由

继续使用独立 public router（history mode），不混入主应用 hash 路由。

| 路由 | 职责 |
| --- | --- |
| `/` | 首页工程门面 |
| `/notes` | 工程笔记列表 |
| `/notes/:slug` | 笔记详情 |
| `/public` | redirect `/` |
| `/*` | redirect `/` |

### 导航

桌面：

- 品牌：`ZeroMadLife / Sage`
- 胶囊导航：`首页 · 体系 · 证据 · 笔记 · 关于`
- 右侧次级：`GitHub ★ N`、`问 Sage`

移动：

- 汉堡菜单
- 抽屉/面板承载完整导航与 GitHub / 问 Sage

说明：

- 首页锚点（体系/证据/关于）与笔记路由并存。
- “问 Sage”保留，但不是第一主 CTA；主 CTA 是“看 Harness 体系 / 看源码”。

## 5. 首页模块设计

顺序固定：

### 5.1 HeroProblem

- 标签：`ENGINEERING SURFACE`
- 标题：强调“不是又一个聊天框 / 是可恢复的学习运行时”
- 支持文案：目标、知识、实践、证据的可审计闭环
- 主按钮：看 Harness 体系
- 次按钮：GitHub 源码
- 右侧：System Snapshot 卡（Timeline / Approval / Recovery / Surfaces）

### 5.2 HarnessSystem

核心证据区，不是装饰：

- Plan：目标拆解
- Tool：受控执行
- Approve：危险操作确认
- Evidence：可回放结果

配套一句边界：刷新/断线后从 durable timeline 恢复，而不是重绘模型状态。

### 5.3 EvidenceGallery

三张真实工作台截面：

- Assistant
- Knowledge
- Practice

每张配一句“可验证路径”，避免概念图措辞。截图优先复用现有 `docs/assets/readme/screenshots/` 或公开站专用压缩资产。

### 5.4 GithubProof

- 仓库：`ZeroMadLife/sage-agent`
- 显示 star（构建时注入）
- 链到源码、关键 package/docs 路径
- star 缺失时只显示 GitHub，不显示 `★ 0` 假数据

### 5.5 NotesPreview

- 最近 2–3 篇工程笔记卡片
- `View all → /notes`

### 5.6 GrowthPath

- 时间线：done / now / later
- 诚实标注当前边界（如公网 harness、HTTPS、租户隔离等未完成项）

### 5.7 Footer

- 品牌与一句话定位
- GitHub / 笔记 / 问 Sage
- 可选 RSS/sitemap 后续再加；第一期可不做完整 feed

## 6. 轻量笔记系统

### 内容形态

静态 Markdown，构建期打包：

```text
frontend/public-content/
  notes/
    why-durable-timeline.md
    approval-is-not-decoration.md
    public-csp-boundary.md
```

Frontmatter 最小字段：

```yaml
title: 为什么 Harness 需要 durable timeline
date: 2026-07-20
summary: 刷新后如何证明副作用已经发生
tags: [harness, timeline]
related:
  - label: packages/sage_harness
    href: https://github.com/ZeroMadLife/sage-agent/tree/dev/sage-v7/packages/sage_harness
```

### 页面

- `/notes`：标题、日期、摘要、tag
- `/notes/:slug`：Markdown 正文 + related 链接

第一期 2–4 篇即可，主题围绕工程落地，不写生活流水。

## 7. Ask Sage：保留并预留有限权限 Harness

### 现在（v1）

- UI：右侧抽屉 `PublicAskSageDrawer`
- 能力：静态公开 corpus 问答
- 网络：无外部请求，CSP `connect-src 'none'`
- 文案：明确“公开资料预览，不是完整 Agent”

### 后续（v2，本期只预留）

- 同一抽屉与消息交互
- adapter 切换到 limited public harness
- 独立 public-only API
- 只读公开 corpus、限速、审计
- 无私人 workspace、无写工具、无私有 memory

### 稳定接口

```ts
type PublicAgentMode = 'static' | 'limited_harness'

type PublicAgentResponse = {
  mode: PublicAgentMode
  answer: string
  sources: PublicAgentSource[]
}

answerPublicProfileQuestion(question: string): Promise<PublicAgentResponse>
```

v1 实现继续走本地 corpus；v2 通过 `VITE_PUBLIC_AGENT_MODE=limited_harness` 切换。  
v2 部署时才能定向放宽 CSP `connect-src` 到 public API origin，不得放宽到私人 API。

## 8. 视觉系统

参考 zlog 的完成度，不复制其“兴趣博客”定位。

### Token

- 主色：`#2F704E`
- 浅底：`#F6F8F6`
- 深底：`#101412`
- 正文：`#1A201C` / `#E8EDE9`
- 次级：`#6B796F` / `#9AABA0`
- 边框：低对比线
- 圆角：导航胶囊 999；卡片 14–16

### 字体与节奏

- 标题/正文：Inter / system-ui
- 代码/标签：JetBrains Mono 或现有 mono 栈
- 比当前公开站更密，减少大面积空白导致的“素”
- 证据标签用 mono，强化工程感

### 动效

- 200–300ms 轻过渡
- 导航 active、卡片 hover 微抬升
- 遵守 `prefers-reduced-motion`
- 不做重粒子/重背景动画

### 主题

- 支持 light / dark
- 默认可跟系统，允许手动切换
- 深色用于提升质感，但浅色也必须完整可用

## 9. 内容与构建数据

```text
frontend/public-content/
  site.meta.json
  home.sections.json
  ask-corpus.json
  github.meta.json          # build-time generated
  notes/*.md
```

### GitHub star 注入

1. `build:public` 前或之中执行脚本请求 GitHub API（CI/本地构建环境）。
2. 写入 `github.meta.json`：`stargazers_count`、`html_url`、`fetched_at`。
3. 前端只读静态 JSON。
4. 失败时降级：显示 GitHub 按钮，不显示虚假 star。

禁止浏览器运行时请求 `api.github.com`（与当前 CSP 冲突，也增加公开站攻击面）。

## 10. 组件拆分

### Shell

- `PublicAppShell.vue`
- `PublicHeader.vue`
- `PublicMobileNav.vue`
- `PublicFooter.vue`
- theme toggle composable

### Home

- `HeroProblem.vue`
- `HarnessSystem.vue`
- `EvidenceGallery.vue`
- `GithubProof.vue`
- `NotesPreview.vue`
- `GrowthPath.vue`

### Notes

- `NotesListView.vue`
- `NoteDetailView.vue`
- `NoteCard.vue`
- `MarkdownArticle.vue`

### Ask

- `PublicAskSageDrawer.vue`
- `publicAgent.ts` adapter（static | limited_harness）

现有 `PublicProfileView.vue` 收敛为首页组装层，或拆空后删除大段内联样式。

## 11. 部署与安全边界

保持现有私有 canary 公开面模型：

- `npm run build:public`
- `infra/docker/sage-public.Dockerfile`
- Caddy public 路由
- 严格安全头

### v1 CSP

继续：

- `connect-src 'none'`
- 不读取私人 env
- 不依赖 API / Postgres / Redis

### 产物门禁

`build:public` 产物不得包含私有应用路由字符串，例如：

- `/assistant`
- `/coding`
- `/settings`
- cloud auth 私人流程

### 域名

- 本地与 IP 部署可先验收
- `sagecompanion.cn` HTTPS 作为后续运维切片，不阻塞公开站前端改造合并

## 12. 实施切片

建议分支：`codex/feat-public-engineering-surface`  
建议 worktree：独立目录，不在仓库根直接改。

| 切片 | 内容 | 完成定义 |
| --- | --- | --- |
| S1 | public shell / nav / footer / theme | 移动汉堡可用，桌面胶囊导航可用 |
| S2 | 首页模块重排与文案 | 60 秒叙事路径可走通 |
| S3 | notes 静态内容与路由 | 至少 2 篇可打开 |
| S4 | Ask Sage 抽屉与 adapter 稳定化 | 静态问答可用，接口形状固定 |
| S5 | GitHub meta 注入 + 测试 + build:public | star 降级策略可测 |
| S6 | 本地 preview 验收，可选部署 public 容器 | 手机宽度无横向溢出 |

每个切片单独可审查、可回滚。

## 13. 测试与验收

### 自动化

- `publicAgent` 单测：命中、未命中、sources
- notes 路由与 frontmatter 解析测试
- shell/nav 关键交互测试
- `npm run build:public`
- 产物扫描：无私有路由泄漏
- `git diff --check`

### 手工

- 390×844 无横向溢出
- 浅/深主题切换
- GitHub 链接正确
- Ask Sage 边界文案可见
- reduced-motion 下无异常动画

### 验收清单

1. 首页先看到问题与 Harness，而不是空泛个人简介。
2. 三张证据图来自真实产品面。
3. 笔记不是 4 条 field notes 附录，而是可点进的文章。
4. GitHub / star 成为可扫读信任信号。
5. Ask Sage 仍在，但不抢工程叙事。
6. 公开站仍可在无后端条件下部署。

## 14. 风险与缓解

| 风险 | 缓解 |
| --- | --- |
| 做成 zlog 克隆而失去工程证明 | 首页模块顺序强制 Harness/证据优先 |
| 单文件继续膨胀 | 强制 shell/section/notes 拆分 |
| star 构建失败 | 优雅降级，不阻断发布 |
| 过早接 public harness | v1 只固定 adapter，不接私人运行时 |
| 截图陈旧或含隐私 | 使用现有已清理截图或重采只读演示数据 |

## 15. 后续（明确不在本期）

1. `sagecompanion.cn` HTTPS 与 README 稳定公开链接。
2. limited public harness API + 限速 + 审计 + CSP 定向放宽。
3. Publishing Studio → 公开 notes 的审核发布链路。
4. 主应用前端治理：拆分 Knowledge/Coding 巨石文件、清理重复文件、统一空态。
5. RSS / sitemap / OG 细节完善。

## 16. 决策记录

- 站点类型：开源项目落地页 + 成长/工程笔记，不是完整博客平台。
- 主访客：面试官 / 技术招聘方。
- 核心证据：Harness 体系设计 + 真实工作台落地。
- 实现路径：公开站 Shell + 模块拆分（方案 B）。
- 质感参考：zlog 的导航、密度、笔记形态；不复制生活博客叙事。
- Ask Sage：保留；v1 静态，v2 有限权限 harness。
- 主应用：本期不动。
- 开发方式：独立 worktree + `codex/*` 分支实现与 PR。
