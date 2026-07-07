# Codex Goal：Sage v2 — 前端体验升级 + Skills 系统

## 任务类型
goal 执行（自驱完成，直到验收通过）

---

## 背景

项目正式更名 **Sage**（原 TourSwarm Coding Agent）。v1 已完成 Pico v3 runtime 架构移植（`core/coding/` 22 个文件，276 测试全绿）。v2 要把前端从"能跑"升级到"好用"，对标 Hermes WebUI 的核心体验，并补齐 Skills 系统。

**完整设计文档**：`docs/superpowers/specs/2026-07-07-sage-v2-design.md`（先读这个再动手）

## 两条红线

1. **旅游侧代码不动**：`agents/`、`mcp_servers/`、`core/verifier.py`、`evals/` 等全部不改
2. **现有测试不破**：`bash scripts/check.sh` 必须全绿，`cd frontend && npm run test -- --run` 必须全绿

## 现有代码形状（改动前先读）

| 文件 | 现状 | 本次改动 |
|------|------|---------|
| `frontend/src/views/CodingView.vue` | 262 行单栏布局（textarea + 消息 + ToolCallTrace） | 重构为三栏布局 |
| `frontend/src/App.vue` | 导航 "旅行/代码" | 品牌改 Sage |
| `frontend/src/api/coding.ts` | 只有 session + stream | 新增 files/file/git/models/skills/mcp |
| `frontend/src/types/api.ts` | 基础事件类型 | 新增文件树/git/skill/model 类型 |
| `frontend/src/components/ToolCallTrace.vue` | 平铺工具调用 | 保留但 CodingView 改用新的折叠组件 |
| `core/coding/context_manager.py` | `DEFAULT_SYSTEM_PROMPT = "You are CodeAssist..."` | 改成 Sage 人设 |
| `core/coding/skills/` | 不存在 | **新增** Skills 系统 |
| `api/coding.py` | session + websocket stream | 新增 7 个 REST 端点 |
| `api/main.py` | coding 配置 | 新增 skills 注册 + models 配置 |

---

## 分阶段实施（按顺序，每阶段绿了再下一阶段）

### 阶段 1：后端 Skills 系统 + API + system prompt

#### 1.1 Skills 核心

新增 `core/coding/skills/`：

**`core/coding/skills/skill.py`** — Skill dataclass + frontmatter 解析
- 移植 Pico 的 `pico/features/skills.py` 的 `Skill` dataclass 和 `parse_frontmatter`
- Skill 字段：name / description / prompt / source / skill_root / allowed_tools
- `render(arguments="")` 方法：替换 `$ARGUMENTS`

**`core/coding/skills/registry.py`** — Skill 注册和发现
- `discover_skills(root, home=None)` → 加载 builtin + user + project
- 加载顺序：bundled → `~/.sage/skills/` → `<repo>/skills/` 或 `<repo>/.coding/skills/`
- 后加载覆盖同名
- `parse_slash_command(text)` → `(command, arguments)`

**`core/coding/skills/bundled/`** — 3 个内置 skill：
- `review/SKILL.md` — 代码审查
- `test/SKILL.md` — 跑测试
- `commit/SKILL.md` — 准备 commit

每个 SKILL.md 用 frontmatter + body 格式（见 spec 第 4.3 节的完整内容）。

**`core/coding/skills/runner.py`** — Skill 注入 engine
- `run_skill(skill, arguments, runtime)` → 把 skill.render(arguments) 作为 user message 注入 engine

#### 1.2 system prompt 改 Sage

`core/coding/context_manager.py` 的 `DEFAULT_SYSTEM_PROMPT` 改为：

```
You are Sage, a personal coding agent running in the user's repository.

You inspect code with tools before editing, verify changes by running tests or
commands, and keep explanations concise. When a task needs multiple steps, use
the todo ledger to track progress.

Return exactly one or more <tool> calls, or one <final> answer.
```

#### 1.3 新增 7 个 API 端点

在 `api/coding.py` 新增（`api/schemas.py` 加对应请求/响应模型）：

```
GET  /api/v1/coding/{session_id}/files?path=.     → 文件树
GET  /api/v1/coding/{session_id}/file?path=...    → 文件内容
GET  /api/v1/coding/{session_id}/git/status       → branch + dirty_count
GET  /api/v1/coding/models                        → 可用模型列表
PATCH /api/v1/coding/{session_id}/model           → 切换会话模型
GET  /api/v1/coding/skills                        → skill 列表
GET  /api/v1/coding/skills/{name}                 → skill 内容
GET  /api/v1/coding/mcp/servers                   → MCP 配置状态（只读）
```

实现要点：
- files/file 端点直接用 `WorkspaceContext.path()` + `Path.iterdir()` / `read_text()`，不走 engine
- git/status 用 `subprocess.run(["git", "branch", "--show-current"], ...)` + `subprocess.run(["git", "status", "--porcelain"], ...)`，3s 超时
- models 从 `core/config/settings.py` 或 `core/llm.py` 的 `_PROVIDERS` 返回
- PATCH model 重建 runtime 的 model client
- skills 从 `SkillRegistry` 返回
- mcp/servers 从 `mcp_servers/registry.py` 的 `build_mcp_config` 返回配置（不实际连接）

#### 1.4 Slash 命令接入 WebSocket

在 `api/coding.py` 的 WebSocket 处理里，检测 `message.content` 以 `/` 开头时：
1. `parse_slash_command(content)` → `(command, arguments)`
2. 从 SkillRegistry 查找 command
3. 找到 → `skill.render(arguments)` → 作为 user_message 传给 `runtime.run_turn()`
4. 找不到 → 返回 error 事件

#### 1.5 验收
- `GET /api/v1/coding/skills` 返回 3 个内置 skill
- `GET /api/v1/coding/{session}/git/status` 返回正确 branch
- `GET /api/v1/coding/{session}/files?path=.` 返回目录列表
- WebSocket 发 `/review` 能触发 skill 展开
- 新增测试覆盖：skill 加载/解析/slash 注入/git status/files

---

### 阶段 2：前端三栏布局 + 文件树 + git

#### 2.1 Pinia Store

新增 `frontend/src/stores/coding.ts`：
- state: `sessions`, `currentSessionId`, `skills`, `mcpServers`, `fileTree`, `currentModel`, `contextUsage`
- actions: `loadSkills()`, `loadMcpServers()`, `loadFiles(path)`, `loadFile(path)`, `loadGitStatus()`, `switchModel(id)`

#### 2.2 三栏布局

重构 `CodingView.vue` 为三栏：

```vue
<template>
  <div class="sage-layout">
    <CodingGitBadge />  <!-- 顶栏 -->
    <div class="sage-body">
      <CodingSidebar />          <!-- 左栏 260px -->
      <CodingChatArea />         <!-- 中栏 flex -->
      <CodingFileTree />         <!-- 右栏 320px -->
    </div>
  </div>
</template>
```

#### 2.3 新增组件

**`CodingSidebar.vue`**（左栏）
- 三个 section：会话列表 / Skills / MCP
- 会话列表：`+ 新建` + 会话项（id 缩写 + 时间）
- Skills：从 store 加载，每项 `/name` + description + source badge，点击展开
- MCP：从 store 加载，每项 name + transport badge + status badge

**`CodingFileTree.vue`**（右栏）
- 面包屑导航（可点击）
- 目录/文件列表（目录优先，单击展开/折叠，双击文件预览）
- 过滤 `.git`/`__pycache__`/`node_modules`

**`CodingFilePreview.vue`**（右栏内）
- 从 `loadFile(path)` 加载内容
- 代码高亮（复用 useMarkdown 的代码块渲染）

**`CodingGitBadge.vue`**（顶栏）
- 显示 `📁 main ●3`（branch + dirty 数）
- 从 store 加载，每 5s 刷新一次

#### 2.4 API 层

`frontend/src/api/coding.ts` 新增：
- `getFiles(sessionId, path)` / `getFile(sessionId, path)`
- `getGitStatus(sessionId)`
- `getModels()` / `patchModel(sessionId, modelId)`
- `getSkills()` / `getSkill(name)`
- `getMcpServers()`

`frontend/src/types/api.ts` 新增对应类型。

#### 2.5 验收
- 三栏布局渲染正确
- 文件树可浏览目录 + 预览文件
- git badge 显示 branch + dirty 数
- 新增前端测试覆盖组件 mount + API mock

---

### 阶段 3：前端 Composer + 模型选择 + context 环

**`CodingComposer.vue`**（中栏底部）
- model 选择器（下拉，从 `getModels()` 加载，切换调 `patchModel()`）
- context 用量环（圆形 SVG，从 engine 事件的 `prompt_chars` 算预算占比）
- textarea（自适应高度，Enter 发送，Shift+Enter 换行）
- Send / Stop 按钮

**context 用量环计算**：
- engine yield `model_requested` 事件里有 `prompt_chars`
- 预算 60000，算百分比，环形显示
- 颜色：<60% 绿 / 60-80% 黄 / >80% 红

#### 验收
- 模型可切换，切换后新消息用新模型
- context 环显示当前用量
- 新增前端测试

---

### 阶段 4：前端工具调用折叠 + 两阶段渲染

**`CodingToolActivity.vue`**（替代 CodingView 里的 ToolCallTrace）

核心设计：
- 一个 turn 的工具调用分组为 `Activity: N tools`
- 默认折叠，点击展开
- 展开后每个工具：icon + name + args 摘要 + status + 耗时
- result 截断，"show more" 展开

两阶段状态：
- `live`（thinking=true）：工具卡可展开，running 的带 spinner
- `settled`（final/step_limit 后）：自动收成 `Activity: N tools`

数据来源：监听 WebSocket 的 `tool_call` / `tool_result` / `final` / `step_limit` 事件。

#### 验收
- 工具调用默认折叠
- 点击可展开看详情
- final 后自动收起
- 新增前端测试

---

### 阶段 5：前端 Skills 面板 + slash 命令

**`CodingSkillCard.vue`**（左栏 Skills section 内）
- 展开看 SKILL.md 内容（Markdown 渲染）
- "使用"按钮：把 `/skill-name` 填入 composer textarea

**Slash 命令补全**：
- textarea 输入 `/` 时触发下拉提示
- 列出可用 skills，方向键导航，Tab/Enter 选择
- 选中后填入 `/skill-name `

#### 验收
- Skills 面板展示 3 个内置 skill
- 点击展开看内容
- "使用"填入输入框
- `/` 触发补全
- `/review` 能跑通代码审查

---

### 阶段 6：验收 + 文档

- `bash scripts/check.sh` 全绿
- `cd frontend && npm run test -- --run` 全绿
- `cd frontend && npm run build` 通过
- `App.vue` 品牌显示 "Sage"
- `README.md` 加 Sage 段落
- `docs/plans/07-SAGE-V2.md` 落地记录
- 浏览器端到端：`/review` 跑通代码审查

---

## 不要做的事

- **不要动旅游侧代码**
- **不要改 `core/coding/` 的 engine/runtime/tools/workspace 等已有模块**（只新增 skills/ 和改 context_manager 的 prompt）
- **不要做 prompt caching 优化**（下一轮）
- **不要做 approval UI / Runs API**（下一轮）
- **不要做 Skill 自学习 / Curator**（长期方向）
- **不要做 Skill 调用统计**（第一版不做）
- **不要做 MCP 实际连接状态探测**（第一版只读配置）
- **不要改 `core/coding/` 目录名**（品牌用 Sage，代码路径不变）
- **不要用 vanilla JS**（保持 Vue3 + Pinia）
- **不要做文件编辑功能**（第一版只读预览）

## 执行顺序

```
阶段 1  后端 skills + API + prompt     ← 地基
阶段 2  前端三栏 + 文件树 + git          ← 布局骨架
阶段 3  前端 composer + model + context ← 交互核心
阶段 4  前端工具折叠 + 两阶段渲染        ← 体验提升
阶段 5  前端 skills 面板 + slash        ← skills 可视化
阶段 6  验收 + 文档
```

每阶段完成后跑 `bash scripts/check.sh` + `cd frontend && npm run test -- --run`，绿了再下一阶段。

## 完成标志

- 所有验收标准满足（见 spec 第 8 节）
- `bash scripts/check.sh` 全绿
- `cd frontend && npm run test -- --run` 全绿
- `cd frontend && npm run build` 通过
- commit message 标注 `sage-v2`
- `docs/plans/07-SAGE-V2.md` 记录落地
