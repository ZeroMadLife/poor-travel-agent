# Codex Goal：Sage v5 - 架构重构 + 前端渐进式升级

## 任务类型
goal 执行（自驱完成，直到验收通过）

---

## 背景

项目代号 **Sage**，位于 `/Users/zeromadlife/Desktop/tour-agent`，分支 `dev/sage-v4`。

v4.1 已完成后端 runtime contract。但当前 `core/coding/` 下 30 个文件平铺，模块边界不清晰。旅游侧代码和 coding 侧混在同一仓库。前端组件也平铺。

v5 分两阶段：
- **v5.0 架构重构**：目录按职责域分 8 个子目录 + 旅游封装成 skill + 前端组件分目录
- **v5.1 前端升级**：Naive UI + diff 可视化 + monaco 编辑器 + xterm 终端

**先读 `docs/plans/10-SAGE-V4.1.md` 了解 v4.1 现状。**

## 两条红线

1. **现有测试不破**：`bash scripts/check.sh` 必须 350 passed，`cd frontend && npm run test -- --run` 必须 58 passed
2. **行为不变**：重构后功能完全不变，只是文件位置和目录结构变化

---

## v5.0 阶段一：架构重构

### 方向一：后端目录按职责域分 8 个子目录

当前 `core/coding/` 下 30 个文件平铺。重构为：

```text
core/coding/
├── engine/              ← 引擎层（模型循环 + 协议解析 + 事件）
│   ├── __init__.py      ← re-export Engine, ApiClient, parse, RunEvent 等
│   ├── engine.py        ← Engine 主循环（从 core/coding/engine.py 移入）
│   ├── helpers.py       ← engine_helpers.py 改名移入
│   ├── model_output.py  ← <tool>/<final> 解析（移入）
│   └── events.py        ← typed RunEvent 契约（移入）
│
├── tools/               ← 工具层（已有，保持位置）
│   ├── base.py          ← RegisteredTool / ToolResult
│   ├── registry.py      ← @register_tool + tool_search + get_active_tools
│   ├── schemas.py
│   ├── file_tools.py
│   ├── shell_tool.py
│   ├── todo_tools.py
│   ├── plan_tools.py
│   └── agent_tools.py
│
├── tool_executor/       ← 工具执行管线（权限治理域）
│   ├── __init__.py
│   ├── executor.py      ← ToolExecutor（从 tool_executor.py 移入）
│   ├── permissions.py   ← PermissionChecker（从 permissions.py 移入）
│   ├── policy.py        ← ToolPolicyChecker（tool_policy.py 改名移入）
│   └── approval.py      ← ApprovalManager + 危险命令检测（从 approval.py 移入）
│
├── context/             ← 上下文层
│   ├── __init__.py
│   ├── manager.py       ← ContextManager（context_manager.py 改名移入）
│   ├── compact.py       ← CompactManager（移入）
│   └── workspace.py     ← WorkspaceContext（移入）
│
├── skills/              ← 技能层（已有，保持 + 加旅游 skill）
│   ├── skill.py
│   ├── registry.py
│   └── bundled/
│       ├── review/
│       ├── test/
│       ├── commit/
│       └── travel/      ← 新增：旅游 domain skill
│
├── memory/              ← 记忆层（占位，后期填充）
│   └── __init__.py
│
├── multiagent/          ← 多Agent层（worker 子agent）
│   ├── __init__.py
│   ├── manager.py       ← WorkerManager（worker_manager.py 改名移入）
│   ├── execution.py     ← worker_execution.py 改名移入
│   └── runtime.py       ← worker_runtime.py 改名移入
│
├── persistence/         ← 持久化层
│   ├── __init__.py
│   ├── session_store.py ← CodingSessionStore（移入）
│   ├── run_store.py     ← RunStore（移入）
│   ├── session_events.py← SessionEventBus（移入）
│   └── todo_ledger.py   ← TodoLedger（移入）
│
├── plan_mode.py         ← Plan mode（太小不单独建目录）
│
└── runtime.py           ← Runtime 组装（顶层，不变，更新 import 路径）
```

**重构规则**：
1. 只移动文件 + 更新 import 路径，不改逻辑
2. 每个子目录的 `__init__.py` re-export 公开接口，让外部 import 路径简洁
3. `runtime.py` 是唯一组装点，更新它的 import 指向新路径
4. 所有测试的 import 路径同步更新
5. `api/coding.py` 的 import 同步更新

**验证**：重构后 `bash scripts/check.sh` 必须全绿，所有测试通过。

### 方向二：旅游侧封装成 Sage 的 domain skill + domain tools

当前旅游代码散在 `agents/`、`mcp_servers/`、`core/verifier.py`、`evals/`。封装成 Sage 的 domain skill + domain tools。

#### 2.1 新增 `/travel` skill

`core/coding/skills/bundled/travel/SKILL.md`：

```markdown
---
name: travel
description: 旅游行程规划（多Agent协作 + 预算约束 + 确定性验证）
allowed-tools: generate_itinerary, search_attractions, get_weather, get_forecast, geocode, search_nearby, get_route
---
你是旅游规划助手。用户想规划旅游行程时：

1. 确认目的地、天数、预算、偏好
2. 调用 generate_itinerary 生成完整行程（内部多Agent协作）
3. 如果用户问天气，调用 get_weather 或 get_forecast
4. 如果用户问附近，调用 search_nearby
5. 预算敏感 - 推荐时考虑学生消费水平
```

#### 2.2 旅游工具注册到 Sage 的 tool registry

在 `core/coding/tools/` 下新增 `travel_tools.py`，把旅游的核心能力注册为 Sage 工具：

```python
@register_tool(
    name="generate_itinerary",
    description="生成完整多日旅游行程（内部多Agent协作：信息->推荐->规划->预算）",
    schema={"destination": "str", "budget_total": "int", "preferences": "str", "dates": "str"},
    schema_model=ItineraryArgs,
    risky=False,
    category="travel",
    deferred=True,  # 延迟加载，通过 tool_search 激活
)
def generate_itinerary(workspace, args, ctx):
    """调用 LangGraph 多Agent图生成行程。"""
    # 复用 agents/itinerary_tool.py 的逻辑
    ...
```

同时把旅游 MCP 工具（search_attractions / get_weather / get_forecast / geocode / search_nearby / get_route）也注册为 deferred tools。

#### 2.3 前端移除旅游视图

- `App.vue` 移除"旅行/代码"切换，默认进入 Sage coding 界面
- `ChatView.vue` 保留但不再是默认视图
- 用户通过 `/travel` skill 在 Sage 界面里使用旅游能力

#### 2.4 旅游侧代码保留但重新组织

- `agents/` -- 保留（LangGraph 图 + itinerary_tool），被 travel_tools.py 调用
- `mcp_servers/` -- 保留（amap/weather/scenic MCP Server），被 travel_tools.py 调用
- `core/verifier.py` -- 保留（确定性验证器），被 generate_itinerary 调用
- `evals/` -- 保留（旅游评测数据）
- `api/routes.py` / `api/ws.py` -- 保留（旅游 chat API），但不作为主入口

**关键**：旅游代码不删，只是从"主产品"降级为"Sage 的 domain skill + domain tools"。

### 方向三：前端组件分目录

当前 7 个 `Coding*.vue` 平铺在 `components/` 下。重构为：

```text
frontend/src/components/coding/
├── chat/                ← 聊天区
│   ├── CodingToolActivity.vue
│   ├── CodingThinkingIndicator.vue
│   └── CodingApprovalCard.vue
├── sidebar/             ← 左栏
│   └── CodingSidebar.vue
├── files/               ← 右栏文件树
│   ├── CodingFileTree.vue
│   └── CodingGitBadge.vue
├── composer/            ← 底部输入
│   └── CodingComposer.vue
└── index.ts             ← re-export
```

`CodingView.vue` 的 import 路径同步更新。

**验证**：`cd frontend && npm run test -- --run` 全绿 + `npm run build` 通过。

---

## v5.1 阶段二：前端渐进式升级（Naive UI + diff + monaco + xterm）

**v5.0 完成后再做 v5.1。** v5.1 的内容见下方，如果 v5.0 已经是完整一轮 goal，v5.1 可以作为后续 goal。

### 方向四：引入 Naive UI

安装 `naive-ui`，逐个组件迁移（NLayout / NMenu / NCollapse / NInput / NSelect / NButton / NTree / NTag / NCard）。

### 方向五：diff 可视化

- 工具结果 diff 自动识别高亮
- 后端新增 `core/coding/context/workspace_diff.py`（WorkspaceDiffTracker）
- 前端新增 `CodingDiffDrawer.vue`（NDrawer + diff 高亮）

### 方向六：monaco 代码编辑器

安装 `monaco-editor`，新增 `CodingCodeEditor.vue`，替换文件预览的 `<pre>`。diff drawer 用 monaco DiffEditor。

### 方向七：xterm 内嵌终端

安装 `@xterm/xterm`，后端新增 WebSocket 终端端点，前端新增 `CodingTerminal.vue`，右栏加 Files/Terminal tab 切换。

---

## 不要做的事

- 不要改 v4.1 的后端逻辑（events/tool_executor/engine/context_manager 只移动不改逻辑）
- 不要删除旅游侧代码（保留，只重新组织调用关系）
- 不要引入 hermes-studio 的 Koa BFF / Electron / Socket.IO
- 不要一次性重写所有前端组件（v5.1 逐个迁移）
- 不要在 v5.0 阶段引入 Naive UI / monaco / xterm（那是 v5.1 的事）

## 执行顺序

```
v5.0 阶段一：架构重构
  方向一  后端目录分 8 个子目录（只移动文件 + 更新 import）
     ↓
  方向二  旅游封装成 domain skill + domain tools
     ↓
  方向三  前端组件分目录
     ↓
  验收    全量测试 + build

v5.1 阶段二：前端升级（v5.0 完成后再做）
  方向四  Naive UI
  方向五  diff 可视化
  方向六  monaco 编辑器
  方向七  xterm 终端
```

## 完成标志（v5.0）

- `bash scripts/check.sh` 全绿
- `cd frontend && npm run test -- --run` 全绿
- `cd frontend && npm run build` 通过
- `core/coding/` 下有 8 个子目录，文件不再平铺
- `/travel` skill 存在且可调用
- 旅游工具注册到 Sage tool registry（deferred=True）
- 前端组件在 `components/coding/` 子目录下
- `App.vue` 默认进入 Sage coding 界面
- commit message 标注 `sage-v5.0`
- `docs/plans/11-SAGE-V5.md` 记录落地

## 参考文件速查

| 要解决的问题 | 参考源 |
|---|---|
| 当前后端结构 | `core/coding/` 下 30 个文件 |
| 当前前端结构 | `frontend/src/components/Coding*.vue` |
| v4.1 events/tool_executor | `core/coding/events.py` + `core/coding/tool_executor.py` |
| 旅游 LangGraph 图 | `agents/itinerary_tool.py` + `agents/graph.py` |
| 旅游 MCP Server | `mcp_servers/amap/` + `mcp_servers/weather/` + `mcp_servers/scenic/` |
| 旅游验证器 | `core/verifier.py` |
| skill 注册机制 | `core/coding/skills/registry.py` |
| tool 注册机制 | `core/coding/tools/registry.py` |
| hermes-studio 参考 | `https://github.com/EKKOLearnAI/hermes-studio`（WebFetch） |
