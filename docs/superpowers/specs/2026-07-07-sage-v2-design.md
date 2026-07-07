# Sage v2 设计 — 前端体验升级 + Skills 系统

> 日期：2026-07-07
> 项目代号：**Sage**（原 TourSwarm Coding Agent）
> 状态：已确认方向，待实施
> 前置：v1 已完成 Pico 架构移植（commit `d966b1a`，分支 `codex/coding-agent-v1`）

---

## 1. 背景与目标

### 1.1 v1 现状

v1 完成了 Pico v3 runtime 架构移植到 tour-agent 的 web 外壳：
- `core/coding/` 22 个 Python 文件，10 层模块（workspace/tools/engine/context/compact/todo/plan/worker/runtime/api）
- 276 后端测试 + 17 前端测试全绿
- 旅游侧零回归

但 v1 的前端极度朴素（CodingView.vue 仅 262 行），只有一个 textarea + 消息列表 + 工具调用 trace。对照 Hermes WebUI 的成熟设计，差距巨大。

### 1.2 v2 目标

**项目正式更名 Sage。** 把前端从"能跑"升级到"好用"，对标 Hermes WebUI 的核心体验，并补齐 Skills 系统。

四个核心交付：
1. **三栏布局重构** —— 会话/skills/MCP | 聊天+工具 | 文件树+预览
2. **Skills 系统** —— 移植 Pico SKILL.md 机制 + 前端可视化面板
3. **文件树 + git 状态** —— 右栏文件浏览 + 顶栏 branch/dirty badge
4. **模型选择 + context 用量** —— composer footer 会话级模型切换 + 上下文余量环

### 1.3 设计哲学

借鉴 Hermes 的 **"calm developer console"** 哲学：
- **工具调用是 metadata 不是 message** —— 视觉优先级低于用户/助手正文
- **渐进式披露** —— 默认折叠，点击展开细节
- **两阶段渲染** —— 运行中 live 展开，结束后收成简短 worklog
- **Composer footer 集中会话作用域控件** —— model/context/send 全在底部

### 1.4 非目标

- 不做 vanilla JS（保持 Vue3）
- 不做 prompt caching 优化（P0 但属后端轨道，下一轮做）
- 不做 Runs API / approval UI（下一轮）
- 不做 Skill 自学习闭环 / Curator（长期方向，本轮只做基础 Skills）
- 不动旅游侧代码
- 不做 Skill 调用统计（第一版先不做）

---

## 2. 项目更名：TourSwarm → Sage

### 2.1 更名范围

| 位置 | 改动 |
|------|------|
| 前端品牌 | "TourSwarm CodeAssist" → "Sage" |
| App.vue 导航 | "旅行/代码" → 保留两个 view，但 coding view 标题改 "Sage" |
| README | 新增 Sage 段落，与旅游助手并列 |
| system prompt | `core/coding/context_manager.py` 的 `DEFAULT_SYSTEM_PROMPT` 改成 Sage 人设 |
| 代码包名 | `core/coding/` 目录名**不改**（避免大规模重命名破坏 v1 测试），仅品牌层用 Sage |

### 2.2 Sage system prompt

```
You are Sage, a personal coding agent running in the user's repository.

You inspect code with tools before editing, verify changes by running tests or
commands, and keep explanations concise. When a task needs multiple steps, use
the todo ledger to track progress.

Return exactly one or more <tool> calls, or one <final> answer.
```

---

## 3. 前端三栏布局

### 3.1 整体结构

```text
┌──────────────────────────────────────────────────────────────┐
│ 顶栏：Sage  |  📁 main ●3  |  ⚙                              │
├───────────┬──────────────────────────────┬───────────────────┤
│ 左栏 260px │ 中栏（flex）                  │ 右栏 320px         │
│           │                              │                   │
│ ─ 会话 ─  │  消息区（scroll）             │ ─ 文件树 ─        │
│ + 新建    │  ├─ user message             │  📁 src/          │
│ • sess-1  │  ├─ Activity: 2 tools ▸      │  ├─ 📁 core/      │
│ • sess-2  │  │  └─ read_file ✓ 12ms      │  ├─ 📁 api/       │
│           │  │  └─ search ✓ 8ms          │  └─ 📄 README.md  │
│ ─ Skills ─│  ├─ assistant: <final>...    │                   │
│ /review   │                              │ ─ 预览 ─          │
│ /test     │  ┌────────────────────────┐ │  README.md        │
│ /commit   │  │ composer footer         │ │  # Sage...        │
│           │  │ [model▾] [ctx环] [📎]   │ │                   │
│ ─ MCP ─   │  │ [textarea...]    [Send] │ │                   │
│ ● amap    │  └────────────────────────┘ │                   │
│ ● weather │                              │                   │
│ ● code    │                              │                   │
└───────────┴──────────────────────────────┴───────────────────┘
```

### 3.2 左栏：会话 + Skills + MCP

三个 section，用分隔线分开：

**会话列表**
- `+ 新建会话` 按钮
- 会话列表（id 缩写 + 最后消息预览 + 时间）
- 点击切换会话
- 当前会话高亮

**Skills 列表**
- 从 `GET /api/v1/coding/skills` 加载
- 每项：`/skill-name` + description + source badge（builtin/user/project）
- 点击展开看 skill 内容预览
- 点击"使用"把 `/skill-name` 填入输入框

**MCP 状态**
- 从 `GET /api/v1/coding/mcp/servers` 加载（新增 API）
- 每项：server 名 + transport badge（stdio） + status badge（●active）
- 第一版只读展示，不做 toggle

### 3.3 中栏：聊天 + 工具 + Composer

**消息区**
- user / assistant 消息（Markdown 渲染，复用现有 useMarkdown composable）
- **工具调用折叠**（核心改动）：
  - 一个 turn 用了 N 个工具，默认折叠成一行 `Activity: N tools ▸`
  - 展开后显示每个工具：icon + name + args 摘要 + status + 耗时
  - result 默认截断，点击"show more"展开
  - **两阶段渲染**：运行中（live）可展开看进度；结束后（settled）自动收成简短 worklog
- error 消息红色显示

**Composer footer**
- model 选择器（下拉，从 `GET /api/v1/coding/models` 加载）
- context 用量环（圆形，显示 token 数 / 预算百分比）
- textarea（自适应高度）
- Send 按钮（disabled 当空输入或 thinking 中）
- Stop 按钮（thinking 中显示，发送 stop 信号）

### 3.4 右栏：文件树 + 预览

**文件树**
- 从 `GET /api/v1/coding/{session_id}/files?path=` 加载
- 目录优先排序，文件按字母
- 单击展开/折叠目录
- 双击文件 → 预览
- 面包屑导航（可点击路径段）
- 过滤 `.git`/`__pycache__`/`node_modules` 等

**文件预览**
- 从 `GET /api/v1/coding/{session_id}/file?path=` 加载
- 代码高亮（复用现有 Markdown 渲染的代码块能力）
- 只读，不支持编辑（第一版）

### 3.5 顶栏：品牌 + git 状态

- 左：Sage 品牌
- 中：git 状态 badge —— `📁 main ●3`（branch 名 + dirty 文件数）
- 右：设置按钮（第一版可只放占位）

---

## 4. Skills 系统

### 4.1 后端：移植 Pico SKILL.md 机制

新增 `core/coding/skills/` 目录：

```text
core/coding/skills/
├── __init__.py
├── skill.py          # Skill dataclass + frontmatter 解析
├── registry.py       # discover_skills（builtin + user + project）
├── bundled/          # 内置 skills
│   ├── review/SKILL.md
│   ├── test/SKILL.md
│   └── commit/SKILL.md
└── runner.py         # skill 展开 + 注入 engine
```

**Skill dataclass**（移植 Pico `features/skills.py`）：

```python
@dataclass(frozen=True)
class Skill:
    name: str                    # slash 命令名
    description: str             # 一句话描述
    prompt: str                  # skill body（markdown）
    source: str                  # "builtin" / "user" / "project"
    skill_root: str              # skill 文件所在目录
    allowed_tools: tuple[str, ...] = ()  # 可选，限制工具集
```

**加载顺序**（后加载覆盖同名）：
1. 内置（`core/coding/skills/bundled/`）
2. 用户（`~/.sage/skills/`）
3. 项目（`<repo>/skills/` 或 `<repo>/.coding/skills/`）

**frontmatter 格式**（与 Pico 兼容）：

```yaml
---
name: review
description: 审查当前代码改动
allowed-tools: read_file, search, list_files
---
请审查当前工作区的代码改动：

1. 用 run_shell 跑 git diff 查看改动
2. 逐文件分析改动质量
3. 指出问题并给出建议
```

### 4.2 Skill 调用流程

**用户 slash 命令调用**：
1. 用户在前端输入 `/review`
2. 前端发 `{"content": "/review"}` 到 WebSocket
3. 后端 `api/coding.py` 检测到 `/` 开头，调 `SkillRegistry.parse_slash_command`
4. 找到 skill → `skill.render()` 展开 prompt → 作为 user message 注入 engine
5. engine 正常跑 ReAct 循环

**agent 自动调用**（第一版可选，不阻塞）：
- engine 的 system prompt 里列出可用 skills
- agent 可以在回复里建议用 skill，但第一版不让 agent 自动触发 slash

### 4.3 三个内置 Skills

**`/review` — 代码审查**
```markdown
---
name: review
description: 审查当前代码改动
allowed-tools: read_file, search, list_files, run_shell
---
请审查当前工作区的代码改动：

1. 用 run_shell 跑 `git diff` 查看改动
2. 逐文件分析改动质量、潜在问题、改进建议
3. 给出审查结论
```

**`/test` — 跑测试**
```markdown
---
name: test
description: 跑测试并整理失败原因
allowed-tools: read_file, search, run_shell
---
请跑项目测试并分析结果：

1. 用 run_shell 跑 `bash scripts/check.sh`（若存在）或 `pytest -q`
2. 如果有失败，分析失败原因
3. 给出修复建议
```

**`/commit` — 准备 commit**
```markdown
---
name: commit
description: 准备 commit 消息和改动摘要
allowed-tools: read_file, search, run_shell
---
请准备本次提交：

1. 用 run_shell 跑 `git status` 和 `git diff --staged`
2. 总结改动内容
3. 建议 commit message（中文，遵循 conventional commits）
4. 不要实际执行 git commit，只给建议
```

### 4.4 前端 Skills 面板

左栏 Skills section：
- `GET /api/v1/coding/skills` 加载列表
- 每项显示：`/review` + "审查当前代码改动" + `[builtin]` badge
- 点击展开：显示完整 SKILL.md 内容（Markdown 渲染）
- "使用"按钮：把 `/review` 填入 composer textarea

---

## 5. 新增后端 API

### 5.1 文件浏览

```
GET /api/v1/coding/{session_id}/files?path=.
→ { "entries": [{"name": "src", "is_dir": true}, {"name": "README.md", "is_dir": false}] }
```
复用 `list_files` 工具逻辑，但不经过 engine，直接调 `WorkspaceContext`。

```
GET /api/v1/coding/{session_id}/file?path=README.md
→ { "path": "README.md", "content": "# Sage...", "lines": 50 }
```
复用 `read_file` 逻辑。

### 5.2 Git 状态

```
GET /api/v1/coding/{session_id}/git/status
→ { "is_git": true, "branch": "main", "dirty_count": 3, "changed_files": ["README.md", ...] }
```
用 `subprocess` 跑 `git branch --show-current` + `git status --porcelain`。

### 5.3 模型管理

```
GET /api/v1/coding/models
→ { "models": [{"id": "deepseek:deepseek-chat", "label": "DeepSeek Chat"}, ...] }
```
从配置返回可用模型列表。

```
PATCH /api/v1/coding/{session_id}/model
Body: {"model_id": "deepseek:deepseek-chat"}
→ { "ok": true }
```
切换会话级模型（重建 model client）。

### 5.4 Skills

```
GET /api/v1/coding/skills
→ { "skills": [{"name": "review", "description": "...", "source": "builtin"}, ...] }
```

```
GET /api/v1/coding/skills/{name}
→ { "name": "review", "content": "---\nname: review\n...\n请审查...", "source": "builtin" }
```

### 5.5 MCP 状态（第一版只读）

```
GET /api/v1/coding/mcp/servers
→ { "servers": [{"name": "code", "transport": "stdio", "status": "active"}, ...] }
```
从 `mcp_servers/registry.py` 读取配置（第一版不实际连接，只返回配置状态）。

---

## 6. 前端组件设计

### 6.1 新增组件

| 组件 | 职责 |
|------|------|
| `CodingSidebar.vue` | 左栏：会话列表 + Skills + MCP |
| `CodingFileTree.vue` | 右栏：文件树 + 面包屑 |
| `CodingFilePreview.vue` | 右栏：文件预览 |
| `CodingComposer.vue` | 中栏底部：model 选择 + context 环 + textarea + send |
| `CodingToolActivity.vue` | 工具调用折叠组（替代现有 ToolCallTrace） |
| `CodingSkillCard.vue` | 左栏 skill 卡片（展开/使用） |
| `CodingGitBadge.vue` | 顶栏 git 状态 badge |

### 6.2 改造组件

| 组件 | 改动 |
|------|------|
| `CodingView.vue` | 从单栏重构为三栏布局，组合上述组件 |
| `App.vue` | 导航品牌改 Sage |
| `api/coding.ts` | 新增 files/file/git/models/skills/mcp API 调用 |
| `types/api.ts` | 新增对应类型 |
| `stores/coding.ts`（新增） | Pinia store 管理会话/skills/模型/文件树状态 |

### 6.3 工具调用折叠设计（CodingToolActivity.vue）

```text
┌─────────────────────────────────────┐
│ 🔧 Activity: 3 tools         ▸     │  ← 默认折叠
└─────────────────────────────────────┘

展开后：
┌─────────────────────────────────────┐
│ 🔧 Activity: 3 tools         ▾     │
│ ├─ 📖 read_file  README.md   ✓ 12ms│
│ │   └─ "# Sage\n个人 Agent..."     │  ← result 截断
│ ├─ 🔍 search  "def Engine"  ✓ 8ms │
│ │   └─ "core/coding/engine.py:30"  │
│ └─ 🛠 run_shell  pytest -q   ✓ 2.1s│
│     └─ "276 passed"                │
└─────────────────────────────────────┘
```

两阶段渲染状态：
- `live`（thinking 中）：工具卡可展开看进度，状态 running 的工具带 spinner
- `settled`（final 后）：自动收成 `Activity: N tools`，点击可重新展开

---

## 7. 实施顺序

```text
Phase 7（Sage v2）
│
├─ 7.1 后端 Skills 系统 + API
│   ├─ core/coding/skills/（skill.py + registry.py + runner.py + bundled/）
│   ├─ 3 个内置 SKILL.md
│   ├─ api/coding.py 新增 7 个端点
│   ├─ system prompt 改 Sage
│   ├─ 验收: skills API 可用，slash 命令走通
│   └─ 测试: skills 加载/解析/slash 注入
│
├─ 7.2 前端三栏布局 + 文件树 + git
│   ├─ CodingView.vue 重构为三栏
│   ├─ CodingSidebar.vue（会话+skills+mcp）
│   ├─ CodingFileTree.vue + CodingFilePreview.vue
│   ├─ CodingGitBadge.vue
│   ├─ api/coding.ts 新增调用
│   ├─ stores/coding.ts（Pinia）
│   ├─ 验收: 三栏可渲染，文件树可浏览，git badge 显示
│   └─ 测试: 组件 mount + API mock
│
├─ 7.3 前端 Composer + 模型选择 + context 环
│   ├─ CodingComposer.vue
│   ├─ model 选择器（GET models + PATCH session model）
│   ├─ context 用量环（从 engine 事件算 token）
│   ├─ 验收: 模型可切换，context 环显示
│   └─ 测试: composer 交互
│
├─ 7.4 前端工具调用折叠 + 两阶段渲染
│   ├─ CodingToolActivity.vue
│   ├─ live/settled 状态机
│   ├─ 替换现有 ToolCallTrace
│   ├─ 验收: 工具调用折叠/展开，final 后自动收起
│   └─ 测试: 折叠/展开交互
│
├─ 7.5 前端 Skills 面板 + slash 命令
│   ├─ CodingSkillCard.vue
│   ├─ skill 列表加载 + 展开 + "使用"
│   ├─ textarea 检测 / 开头 → slash 命令提示
│   ├─ 验收: skills 面板展示，/review 可调用
│   └─ 测试: skill 面板交互
│
└─ 7.6 验收 + 文档
    ├─ bash scripts/check.sh 全绿
    ├─ cd frontend && npm run test -- --run 全绿
    ├─ cd frontend && npm run build 通过
    ├─ README 更新 Sage 段落
    ├─ docs/plans/07-SAGE-V2.md 落地记录
    └─ 浏览器端到端：/review 跑通代码审查
```

---

## 8. 验收标准

1. `bash scripts/check.sh` 全绿，旅游侧零回归
2. `cd frontend && npm run test -- --run` 全绿
3. `cd frontend && npm run build` 通过
4. 前端三栏布局可渲染
5. 文件树可浏览目录 + 预览文件
6. 顶栏显示 git branch + dirty 数
7. composer 可切换模型
8. context 用量环显示
9. 工具调用默认折叠，可展开，final 后自动收起
10. Skills 面板展示 3 个内置 skill
11. `/review` slash 命令走通代码审查
12. system prompt 是 Sage 人设
13. 前端品牌显示 "Sage"

---

## 9. 风险与应对

| 风险 | 应对 |
|------|------|
| 三栏布局在小屏幕下挤压 | 右栏默认收起，左栏可折叠；<720px 时左栏滑出 |
| 文件树大目录性能 | 单层加载（不递归），上限 200 条，惰性展开 |
| git subprocess 超时 | 3s 超时，失败时 badge 显示 "git unavailable" |
| 模型切换后 engine 状态丢失 | 只换 model client，保留 history 和 workspace |
| skill slash 命令和普通消息冲突 | 严格匹配 `^/\w+` 开头才走 skill 解析 |
| 工具折叠状态丢失 | per-session 记忆展开状态（localStorage） |

---

## 附录：命名决策

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-07-07 | 项目更名 Sage | "智者"，强调知识/记忆沉淀和 Skills 自学习，顶替简历 Pico 位置 |
| 2026-07-07 | 保持 `core/coding/` 目录名不改 | 避免 v1 测试大规模重命名，品牌层用 Sage 即可 |
| 2026-07-07 | Skills 用 Pico 兼容的 SKILL.md frontmatter | 未来可复用 Pico/agentskills.io 生态的 skill |
| 2026-07-07 | MCP 面板第一版只读 | 实际连接状态探测工作量大，第一版只展示配置 |
