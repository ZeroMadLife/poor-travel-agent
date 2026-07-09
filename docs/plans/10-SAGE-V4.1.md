# Sage v4.1 Runtime Contract 落地记录

> 日期：2026-07-09
> 分支：`dev/sage-v4`
> 目标：System Prompt 7 层、typed RunEvent、ToolExecutor 边界、脚本化 agent loop 测试、前端事件/stream 分层。

## 基线

重构前先跑通当前基线：

```bash
bash scripts/check.sh
# 329 passed, 16 warnings

cd frontend && npm run test -- --run
# 51 passed
```

执行前工作区已有用户修改：

```text
M docs/superpowers/prompts/2026-07-09-codex-goal-sage-v4.1.md
```

本轮没有覆盖该 prompt 文件。

## 实际落地

### 1. System Prompt 7 层与动态边界

- `core/coding/context_manager.py` 新增 `SYSTEM_PROMPT_DYNAMIC_BOUNDARY`。
- `DEFAULT_SYSTEM_PROMPT` 扩展为 7 层静态核心：System、Doing tasks、Executing actions with care、Using your tools、Tone and style、Output efficiency、Response protocol。
- prompt 输出顺序调整为：稳定核心 + active tools、动态边界、workspace reminder、deferred tools、session date。
- `SAGE.md` / `AGENTS.md` 由 `CodingRuntime` 作为 render-only reminder 读取并传入 `ContextManager`，不写入 `session["history"]`。

### 2. Typed RunEvent Contract

- 新增 `core/coding/events.py`，用 Pydantic v2 定义 runtime event。
- 所有 event 默认带 `run_id` 和 `created_at`，并通过 `event_to_dict()` 转成现有 JSON-safe dict。
- `ToolResultEvent` 保留兼容字段：`tool`、`args`、`content`、`is_error`、`policy_reason`、`security_event_type`。
- `CodingRuntime` 将 `turn_started` / `turn_finished` 写入 trace 和 event bus；WebSocket 主流仍保持聊天事件为主。

### 3. ToolExecutor 拆分

- 新增 `core/coding/tool_executor.py`，负责单个 tool payload 的 normalize、permission、policy、approval wait、tool call、tool result、cancel check。
- `Engine` 保留模型循环、history append、parse、retry/final/step_limit orchestration。
- `Engine` 消费 `ToolResultEvent` 后再写入 tool history，避免 ToolExecutor 直接耦合 session store / run store / WebSocket。

### 4. 脚本化 Agent Loop 测试

- 新增 `tests/core/coding/scripted_api_client.py`。
- 新增 `tests/core/coding/test_agent_loop.py`，覆盖 user -> final、user -> tool -> final、policy denied -> final、approval -> tool -> final、step_limit。
- 测试不调用真实 LLM API。

### 5. 前端事件与 Stream 分层

- 新增 `frontend/src/stores/codingEvents.ts`，集中处理 server event 到 UI state 的归约。
- 新增 `frontend/src/stores/codingStream.ts`，封装 WebSocket connect / send / stop / disconnect，并防止旧 socket 事件污染新 session。
- `frontend/src/stores/coding.ts` 保持 `useCodingStore()` 对外 API 不变，继续负责 approval preview、workspace refresh、session/run loaders。
- `frontend/src/types/api.ts` 补充 `run_id` / `created_at`、`approval_granted`、`turn_started`、`turn_finished` 等事件类型。

## 验证结果

已通过的阶段性验证：

```bash
pytest tests/core/coding/test_context_compact.py \
  tests/core/coding/test_events.py \
  tests/core/coding/test_tool_executor.py \
  tests/core/coding/test_agent_loop.py \
  tests/core/coding/test_engine.py \
  tests/core/coding/test_run_store.py \
  tests/api/test_coding_routes.py -q
# 56 passed

ruff check core/coding tests/core/coding tests/api/test_coding_routes.py
# All checks passed

mypy core/
# Success: no issues found

cd frontend && npm run test -- --run
# 58 passed

cd frontend && npm run build
# build passed
```

全量验收：

```bash
bash scripts/check.sh
# ruff lint passed
# ruff format --check passed
# mypy passed: 85 source files
# pytest passed: 350 passed, 16 warnings

cd frontend && npm run test -- --run
# 58 passed

cd frontend && npm run build
# build passed
```

浏览器自动化联调：

- 后端：使用真实 `create_app()` 启动 smoke server，仅将 coding model factory 替换为脚本化模型，避免消耗真实 LLM 额度。
- 前端：使用 Vite dev server 同源 `/api` proxy 连接后端。
- 输入：`读 README.md 告诉我项目叫什么`。
- 结果：
  - WebSocket 已连接。
  - 页面显示 `Activity: 1 tool / 1 done`。
  - 最新 run trace 确认工具调用为 `read_file`。
  - Assistant 最终回复：`README.md 显示项目是 Sage — Personal Web Coding Agent。`
  - Runs 列表出现 completed run，显示 `1 tools · 9 events · final`。
  - session replay 只显示真实用户消息与 assistant 回复，没有 `SAGE.md` / `AGENTS.md` reminder 伪消息。
- 截图：`/tmp/sage-smoke/sage-v4.1-smoke-final.png`。

## 后续项

- v4.2 可以继续做 live run reattach，让刷新页面后可重新挂载运行中的 WebSocket stream。
- 前端后续可把 approval preview、workspace refresh、run/session loaders 进一步拆出 store，但本轮为了稳定没有扩大改动面。
- 后端后续可把 `ToolExecutor` 升级为更完整的 tool policy / permission gate interface，为 sandbox 和 provider profile 做准备。
