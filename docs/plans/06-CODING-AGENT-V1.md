# Phase 6 Coding Agent v1 落地记录

## 目标

把本机 Pico v3 的 runtime / engine / tools 思路迁移到 TourSwarm 的 Web 外壳里，形成一个浏览器可用的个人 Coding 助手：

```text
用户输入 coding 任务
  -> WebSocket 流式传给后端
  -> CodingRuntime 组装 workspace / tools / engine / policy
  -> 模型输出 <tool> 或 <final>
  -> 后端执行工具并流式返回 tool_call / tool_result / final
```

本阶段只新增 Coding 能力，不替换旅游侧。旅游相关的 `agents/graph.py`、`agents/itinerary_tool.py`、`mcp_servers/`、`core/verifier.py`、`evals/` 保持隔离。

## 实际模块

| 层 | 文件 | 设计要点 |
|----|------|----------|
| Layer 0 | `core/coding/workspace.py` | 工作目录上下文、root 逃逸防护、read freshness、输出截断 |
| Layer 1 | `core/coding/tools/base.py`, `schemas.py`, `registry.py` | `RegisteredTool` / `ToolResult` 抽象，6 个核心工具：list/read/search/shell/write/patch |
| Layer 2 | `core/coding/permissions.py`, `tool_policy.py` | 权限层处理 risky/write scope/plan mode，策略层处理 patch 前 fresh read 和 shell 搜索拦截 |
| Layer 3 | `model_output.py`, `engine.py`, `engine_helpers.py` | 解析 `<tool>` / `<final>`，异步 generator 产出可流式事件 |
| Layer 4 | `context_manager.py`, `compact.py` | 固定预算 prompt 组装，长历史折叠为 `compact_summary` |
| Layer 5 | `todo_ledger.py` | `todo_add` / `todo_update` / `todo_list` 工具和 session 内任务账本 |
| Layer 6 | `plan_mode.py` | `enter_plan_mode` / `exit_plan_mode`，plan 文件落 `.coding/plans/`，plan mode 下禁止 risky 工具 |
| Layer 7 | `worker_manager.py`, `worker_execution.py`, `worker_runtime.py` | `agent` / `send_message` / `task_stop`，后台线程运行受限 worker / Explore 子 agent |
| Layer 8 | `runtime.py`, `session_store.py`, `session_events.py`, `run_store.py` | 组装完整 session 状态，持久化 session JSON、events JSONL、run trace |
| Layer 9 | `api/coding.py`, `api/main.py`, `api/schemas.py` | 新增 Coding REST session 和 WebSocket stream，与旅游 chat 路由并行 |
| Layer 10 | `frontend/src/views/CodingView.vue`, `frontend/src/api/coding.ts`, `frontend/src/App.vue` | 顶部导航切换“旅行/代码”，CodeAssist 展示消息和工具调用过程 |

## 关键设计

- **Web 适配而不是 CLI 复制**：保留 Pico 的 engine/runtime/tools 核心循环，丢弃 TUI/CLI/provider profile/sandbox，输出变成 WebSocket event。
- **工具协议简单明确**：模型必须输出 `<tool>{"name":"read_file","args":{"path":"README.md"}}</tool>` 或 `<final>...</final>`，后端解析后决定是否执行。
- **两层工具治理**：PermissionChecker 处理能不能做，ToolPolicyChecker 处理该不该这么做。典型约束是 patch/write 前要 fresh read，shell 不用来替代 read/search/list。
- **文件系统安全优先**：所有路径都经 `WorkspaceContext.path()` 解析，禁止 `../../` 逃逸 workspace root。
- **旅游侧零替换**：Coding runtime 独立在 `core/coding/`，API 和前端只新增并列入口。

## 验收记录

| 命令 | 结果 |
|------|------|
| `conda run -n tour-agent-phase1 pytest tests/core/coding -q` | 34 passed |
| `conda run -n tour-agent-phase1 pytest tests/core/coding tests/api/test_coding_routes.py -q` | 37 passed |
| `conda run -n tour-agent-phase1 ruff check core/coding api tests/core/coding tests/api/test_coding_routes.py` | passed |
| `conda run -n tour-agent-phase1 mypy core/coding api` | passed |
| `conda run -n tour-agent-phase1 bash scripts/check.sh` | ruff + format + mypy + 276 pytest passed |
| `cd frontend && npm run test -- --run` | 11 files / 17 tests passed |
| `cd frontend && npm run build` | passed |
| Browser E2E with fake coding model | CodeAssist connected, streamed `read_file`, and rendered final answer |

## 本地联调

启动后端：

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload --env-file .env
```

启动前端：

```bash
cd frontend
VITE_API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev
```

浏览器打开 `http://127.0.0.1:5173/`，顶部切到“代码”，输入：

```text
读 README.md 告诉我项目叫什么
```

期望事件序列：

```text
tool_call(read_file)
tool_result(read_file)
final
```

## 后续优化

- 增加人工审批 UI：risky 工具进入 pending 状态，前端确认后再执行。
- 增加 diff 预览：`patch_file` / `write_file` 在执行前后展示变更。
- 增加 sandbox：macOS 本地先做目录约束，后续服务器可接容器隔离。
- 增加 benchmark：用固定 coding tasks 测任务完成率、工具调用轮数、失败类型、回滚率。
- 增加长任务 observability：run report、错误分类、工具耗时统计、模型 token 成本。
