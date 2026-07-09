# Codex Goal: Sage v4.1 Runtime Contract 可执行需求稿

> 日期：2026-07-09
> 项目：`/Users/zeromadlife/Desktop/tour-agent`
> 建议分支：`dev/sage-v4` 或新的 `codex/sage-v4.1-runtime-contract`
> 用途：交给项目开发执行。本文是开发需求说明，不是产品宣传稿。

## 0. 可行性结论

**可行，但必须分阶段做。**

当前项目已经完成 Sage v3 的核心地基：

- `core/coding/` 已有独立 `CodingRuntime`、`Engine`、工具注册、approval、run/session store、worker/todo/plan 能力。
- prompt caching 已存在，但 `DEFAULT_SYSTEM_PROMPT` 仍是 3 行核心提示。
- `Engine` 已能产出 `model_requested`、`model_parsed`、`tool_call`、`tool_result`、`final`、`cancelled` 等流式 dict 事件。
- `RunStore` 已把 dict trace 持久化，并派生 timeline。
- 前端 `frontend/src/stores/coding.ts` 已支撑 WebSocket、事件处理、approval、session/run 切换、文件树、git 状态等完整工作台流程。
- 当前测试基线：`pytest --collect-only -q tests` 可收集 **329** 个后端测试；`cd frontend && npm run test -- --run` 当前 **51 passed**。

v4.1 要解决的是结构性问题：事件契约没有后端类型源头，`Engine` 职责过宽，前端 coding store 过胖，system prompt 还没有达到可长期缓存和扩展的形态。

**不要把本轮做成一次“大爆炸重构”。** 推荐按照本文 Phase 0-5 依次完成，每个 phase 都有独立测试和回滚边界。

## 1. 当前进度判断

### 已完成

- v3 prompt caching：`ContextManager.build_system_prompt_once()` 已存在。
- 工具系统装饰器化：`core/coding/tools/registry.py` 与各工具模块已拆分。
- deferred `tool_search`：已能激活延迟工具并持久化到 session。
- approval 闭环：ask 模式、pending/respond API、前端 approval card 与 diff preview 已有。
- stop/cancel：runtime stop flag、approval cancel、WebSocket cancelled event 已有。
- run/session history：trace、timeline、session list、resume、message replay 已有。
- 前端工作台：三栏 UI、文件树、git badge、run/session sidebar、skills/model loading 已有。

### 尚未完成

以下 v4.1 目标文件目前尚未落地：

- `core/coding/events.py`
- `core/coding/tool_executor.py`
- `tests/core/coding/test_events.py`
- `tests/core/coding/test_tool_executor.py`
- `tests/core/coding/test_agent_loop.py`
- `tests/core/coding/scripted_api_client.py`
- `frontend/src/stores/codingEvents.ts`
- `frontend/src/stores/codingStream.ts`

因此本需求不是“补几个漏项”，而是一次 runtime contract 小型重构。

## 2. 推荐执行策略

### 方案 A：一次性全量重构

把 prompt、events、ToolExecutor、Engine、前端 store 一次性改完。

优点：提交少，看起来完整。

风险：失败面太大，后端事件顺序、approval 等待、session replay、前端消息收束很容易互相影响。

不推荐。

### 方案 B：只做 typed events，不拆 Engine 和前端

先新增 `events.py`，只让现有 `Engine` 构造 Pydantic event 后再 dump 成 dict。

优点：风险最低。

缺点：没有解决 Engine 过胖，也不能为端到端 agent loop 测试建立真正边界。

可作为降级方案，不作为本轮推荐目标。

### 方案 C：分阶段完成 v4.1

按以下顺序推进：

1. System prompt 7 层与动态边界。
2. typed `RunEvent` 契约。
3. `ToolExecutor` 从 `Engine` 拆出。
4. `ApiClient` / `ToolExecutor` 双协议与 scripted loop 测试。
5. 前端事件归约与 WebSocket lifecycle 分层。

优点：每一步都能独立测试，保留现有 API 和 UI 行为。

**推荐方案：C。**

## 3. 非目标与红线

### 不要改

- 不改旅游侧主逻辑：`agents/`、`mcp_servers/amap|weather|scenic`、`core/verifier.py`、`evals/`。
- 不重写 `core/llm.py` provider 层。
- 不做 live run reattach，这留给 v4.2。
- 不引入 Hermes provider profile、gateway、cron、sandbox、plugin 全套系统。
- 不重写前端视觉设计，不把 Vue 改成 vanilla JS。
- 不改变现有 REST / WebSocket URL。
- 不破坏 v3 已有 approval、run history、session history、tool_search、stop/cancel。

### 必须保持

- `bash scripts/check.sh` 通过。
- `cd frontend && npm run test -- --run` 通过。
- 现有用户可见工作流不变：创建 session、发送消息、工具调用、approval、stop、run/session 切换仍可用。
- WebSocket 仍发送 JSON-safe dict；前端不感知 Python 类名。

## 4. 目标架构

### 后端目标链路

```text
api/coding.py
  -> CodingRuntime.run_turn()
       -> create run_id
       -> TurnStartedEvent
       -> Engine.run_turn()
            -> ContextManager.build()
            -> ApiClient.complete(prompt)
            -> parse(model output)
            -> ToolExecutor.execute(payload)
                 -> normalize payload
                 -> permission check
                 -> policy check
                 -> approval wait
                 -> RegisteredTool.execute()
                 -> typed tool events
       -> RunStore.append_trace(event_to_dict(event))
       -> SessionEventBus.emit(type, dict)
       -> websocket.send_json(dict)
       -> TurnFinishedEvent
```

### 前端目标链路

```text
CodingView.vue
  -> useCodingStore()
       -> codingStream.ts
            -> connect / send / stop / disconnect
       -> codingEvents.ts
            -> applyCodingEvent(state, event)
       -> coding.ts
            -> session/run/workspace loaders
            -> approval preview enrichment
            -> public store API
```

## 5. Phase 0：保护基线

### 目标

在任何重构前固定当前行为，避免“看似重构，实际改坏现有能力”。

### 要做

1. 运行并记录：

```bash
bash scripts/check.sh
cd frontend && npm run test -- --run
```

2. 如果全量后端太慢，至少先跑：

```bash
pytest tests/core/coding tests/api/test_coding_routes.py -q
cd frontend && npm run test -- --run
```

3. 确认以下文件当前不存在或仍未实现，作为 v4.1 起点：

```text
core/coding/events.py
core/coding/tool_executor.py
frontend/src/stores/codingEvents.ts
frontend/src/stores/codingStream.ts
```

### 验收

- 开发者在提交说明里记录测试基线。
- 没有功能代码改动。

## 6. Phase 1：System Prompt 7 层与动态边界

### 问题

`core/coding/context_manager.py` 当前的 `DEFAULT_SYSTEM_PROMPT` 只有 3 行，无法长期承载工具偏好、行动安全、输出风格和 prompt injection 防护。

### 要做

1. 在 `core/coding/context_manager.py` 增加：

```python
SYSTEM_PROMPT_DYNAMIC_BOUNDARY = "__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__"
```

2. 将 `DEFAULT_SYSTEM_PROMPT` 改为零插值、byte-stable 的 7 层静态核心。

建议层级：

- `# System`
- `# Doing tasks`
- `# Executing actions with care`
- `# Using your tools`
- `# Tone and style`
- `# Output efficiency`
- `# Response protocol`

3. `build_system_prompt_once()` 输出结构调整为：

```text
[cacheable stable core]
[cacheable active tool schemas / active tool descriptions]
__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__
[render-only workspace reminders]
[deferred tool names]
[volatile session date]
```

注意：active tool schemas 会随 `activated_tools` 变化，仍可用当前 `tools_key` 缓存；边界的意义是未来接 provider cache control 时有明确切点。

4. `SAGE.md` / `AGENTS.md` 处理：

- 如果 workspace root 有 `SAGE.md` 或 `AGENTS.md`，内容不能进入 system prompt。
- 内容应作为 render-only 的 user reminder 注入 prompt。
- 不要把 reminder 当普通用户消息持久化到 `session["history"]`，否则 session replay 会显示伪造用户消息。
- 建议在 `CodingRuntime` 或 `ContextManager` 增加 reminder 渲染入口，而不是只在 WebSocket handler 里拼接用户输入。

### 测试

新增或更新 `tests/core/coding/test_context_compact.py`：

- system prompt 包含 7 层关键 heading。
- `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 存在。
- boundary 位于 stable/tool 区之后、volatile date 之前。
- `SAGE.md` / `AGENTS.md` 内容不出现在 boundary 前。
- reminder 不进入 session replay 的普通 `user` / `assistant` message。

### 验收

- `pytest tests/core/coding/test_context_compact.py -q` 通过。
- 现有 prompt caching 测试仍通过。

## 7. Phase 2：Typed RunEvent Contract

### 问题

当前事件是松散 dict。`RunStore`、WebSocket、前端类型都靠约定维持，一旦字段遗漏或拼错，后端源头没有保护。

### 要做

1. 新增 `core/coding/events.py`。

首批事件：

```text
turn_started
model_requested
model_parsed
tool_call
approval_required
approval_granted
tool_result
retry
final
step_limit
cancelled
error
turn_finished
```

2. 每个事件必须包含：

```python
type: Literal["model_requested"]  # each subclass uses its own literal event type
run_id: str = ""
created_at: str = Field(default_factory=now)
```

3. `ToolResultEvent` 必须保留现有兼容字段：

```python
tool: str
args: dict[str, Any]
content: str
is_error: bool = False
policy_reason: str | None = None
security_event_type: str | None = None
```

4. 新增：

```python
RunEvent: TypeAlias = (
    TurnStartedEvent
    | ModelRequestedEvent
    | ModelParsedEvent
    | ToolCallEvent
    | ApprovalRequiredEvent
    | ApprovalGrantedEvent
    | ToolResultEvent
    | RetryEvent
    | FinalEvent
    | StepLimitEvent
    | CancelledEvent
    | ErrorEvent
    | TurnFinishedEvent
)

def event_to_dict(event: RunEventBase) -> dict[str, Any]:
    return event.model_dump()
```

5. `CodingRuntime.run_turn()` 可以先继续对外 yield dict，但 dict 必须来自 typed event 的 `event_to_dict()`。

### 测试

新增 `tests/core/coding/test_events.py`，覆盖：

- tool call/result JSON-safe serialization。
- `run_id` 与 `created_at` 默认存在。
- approval event 字段稳定。
- terminal event `final` / `cancelled` / `step_limit` 保留 `content`。
- optional policy/security 字段可序列化。

### 验收

- `pytest tests/core/coding/test_events.py -q` 通过。
- `pytest tests/core/coding/test_run_store.py -q` 通过。
- WebSocket/API 仍接受额外 `run_id` / `created_at` 字段。

## 8. Phase 3：ToolExecutor 从 Engine 拆出

### 问题

`core/coding/engine.py` 当前同时负责模型循环、payload normalization、permission、policy、approval 等待、工具执行、事件构造和 history 写入。继续堆功能会让 Engine 难测、难换、难复用。

### 边界原则

- `Engine` 保留：history append、prompt build、model call、parse、loop control、step limit、final/retry/cancel orchestration。
- `ToolExecutor` 负责：单个 tool payload 从输入到 typed tool/approval/result events 的完整执行链路。
- `ToolExecutor` 不直接写聊天历史；Engine 消费 `ToolResultEvent` 后再决定是否写入 `history`。
- `ToolExecutor` 不知道 WebSocket、RunStore、SessionStore。

### 要做

1. 新增 `core/coding/tool_executor.py`。

建议构造参数：

```python
class ToolExecutor:
    def __init__(
        self,
        tools: dict[str, RegisteredTool],
        workspace: WorkspaceContext,
        permission_checker: PermissionChecker,
        policy_checker: ToolPolicyChecker,
        approval_manager: ApprovalManager | None = None,
        session_id: str = "",
        should_stop: Callable[[], bool] | None = None,
        run_id: str = "",
    ) -> None:
        raise NotImplementedError
```

2. 提供：

```python
async def execute(self, payload: Any) -> AsyncIterator[RunEventBase]:
    raise NotImplementedError
```

3. 执行顺序必须保持：

```text
normalize payload
unknown tool -> ToolResultEvent(error)
permission check -> ToolResultEvent(error, security_event_type)
policy check -> ToolResultEvent(error, policy_reason)
approval required -> ApprovalRequiredEvent -> wait -> ApprovalGrantedEvent or ToolResultEvent(error)
ToolCallEvent
RegisteredTool.execute()
ToolResultEvent
stop check -> CancelledEvent
```

4. `Engine._execute_tool_payload()` 删除或变成委托：

```python
async for event in self.tool_executor.execute(tool_payload):
    yield event_to_dict(event)
```

5. 保持现有 approval 行为：

- 300 秒超时。
- stop 时唤醒 pending approval。
- session-level approval pattern 仍可跳过重复审批。

### 测试

新增 `tests/core/coding/test_tool_executor.py`，覆盖：

- unknown tool。
- permission denied。
- policy denied。
- auto approval path。
- ask approval granted。
- ask approval denied。
- stop before execution。
- successful `read_file` event order。

更新 `tests/core/coding/test_engine.py`：

- 现有事件顺序仍稳定。
- Engine 收到 `ToolResultEvent` 后仍写入 tool history。
- cancelled path 不重复写 assistant stopped message。

### 验收

- `pytest tests/core/coding/test_tool_executor.py tests/core/coding/test_engine.py -q` 通过。
- `Engine` 体积明显下降，工具执行细节不再散落在 Engine 内部。

## 9. Phase 4：ApiClient / ToolExecutor 双协议与端到端 loop 测试

### 问题

当前已有 `ModelClient` Protocol，但 agent loop 测试仍主要围绕 `Engine` 内部行为。v4.1 需要一个不用真实 API 的端到端脚本化测试，证明：user -> model -> tool -> model -> final 可以稳定跑完。

### 要做

1. 在 `core/coding/engine.py` 中把 `ModelClient` 明确为 `ApiClient`，或保留 `ModelClient` 并新增兼容别名：

```python
class ApiClient(Protocol):
    async def complete(self, prompt: str) -> str:
        raise NotImplementedError
```

2. 新增 `tests/core/coding/scripted_api_client.py`：

```python
class ScriptedApiClient:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.prompts: list[str] = []

    async def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self._responses:
            return "<final>done</final>"
        return self._responses.pop(0)
```

3. 新增 `tests/core/coding/test_agent_loop.py`：

覆盖场景：

- user -> tool -> final。
- user -> final。
- user -> policy denied -> final。
- user -> approval -> tool -> final。
- model never finishes -> step_limit。

4. 如果为了测试需要注入 executor，优先给 `Engine` 增加显式 `tool_executor` 参数或 executor factory，避免测试硬 patch 私有方法。

### 验收

- `pytest tests/core/coding/test_agent_loop.py -q` 通过。
- 不打真实 LLM API。
- loop 测试断言 typed event / dict event 的稳定顺序。

## 10. Phase 5：前端事件归约与 Stream 分层

### 问题

`frontend/src/stores/coding.ts` 目前同时负责 WebSocket lifecycle、server event 处理、消息归约、approval polling、session/run loaders、文件树和 git 刷新。v4.1 不需要重画 UI，但需要先切出两个边界。

### 要做

1. 新增 `frontend/src/stores/codingEvents.ts`。

职责：

- 处理 `model_requested`、`tool_call`、`tool_result`、`approval_required`、`final`、`step_limit`、`cancelled`、`error`。
- 保持当前 UI 行为：tool running/done/error、final 收束 thinking message、terminal event 刷新 run/session。
- 可以先设计为操作一个轻量 state adapter，而不是强求完全纯函数。

2. 新增 `frontend/src/stores/codingStream.ts`。

职责：

```typescript
export class CodingStream {
  connect(sessionId: string): void
  send(content: string): void
  stop(): void
  disconnect(): void
}
```

要求：

- 支持注入 `WebSocket` factory，方便 Vitest 测试。
- session switch 时旧 socket 关闭后不能继续写入新 session state。
- onmessage 只负责 parse JSON 并回调 `onEvent`。

3. 精简 `coding.ts`：

- 保持 `useCodingStore()` 对外 API 不变。
- `handleServerEvent()` 可以保留为 wrapper，但内部委托 `codingEvents.ts`。
- `connectSocket()` / `disconnect()` 委托 `CodingStream`。
- approval diff preview、workspace refresh、loadSessions/loadRuns 仍可留在 store，本轮不追求完全拆干净。

4. 更新 `frontend/src/types/api.ts`：

- 给 coding runtime events 增加可选 `run_id?: string`、`created_at?: string`。
- 增加 `turn_started` / `turn_finished` 类型，前端可忽略但类型要能接住。

### 测试

新增：

- `frontend/src/stores/codingEvents.test.ts`
- `frontend/src/stores/codingStream.test.ts`

更新：

- `frontend/src/stores/coding.test.ts`
- 必要时更新 `frontend/src/api/coding.test.ts`

测试覆盖：

- `tool_call` append tool activity。
- `tool_result` 更新最近 running tool。
- terminal event 收束 assistant thinking message。
- `approval_required` 设置 pending approval。
- stream connect/send/disconnect。
- 关闭旧 stream 后旧 event 不污染新 session。

### 验收

```bash
cd frontend && npm run test -- --run
cd frontend && npm run build
```

全部通过。

## 11. 全量验收

完成后必须跑：

```bash
bash scripts/check.sh
cd frontend && npm run test -- --run
cd frontend && npm run build
```

并做一次人工 smoke test：

1. 启动后端和前端。
2. 创建或进入 Coding 工作台。
3. 输入：`读 README.md 告诉我项目叫什么`
4. 观察：
   - 出现模型请求状态。
   - 出现 `read_file` 工具活动。
   - 最终 assistant 回复正常。
   - Runs 里能看到该 run。
   - run timeline 可读。
   - session replay 不显示 `SAGE.md` / `AGENTS.md` reminder 伪消息。

## 12. 完成标志

- `core/coding/events.py` 存在并有测试。
- `core/coding/tool_executor.py` 存在并有测试。
- `Engine` 不再直接实现完整工具执行链路。
- `DEFAULT_SYSTEM_PROMPT` 是 7 层静态核心。
- `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 存在且有测试。
- `SAGE.md` / `AGENTS.md` 不进入 system prompt，不污染普通 session replay。
- `ScriptedApiClient` 和端到端 agent loop 测试存在。
- `frontend/src/stores/codingEvents.ts` 与 `codingStream.ts` 存在。
- 现有后端、前端测试和前端 build 全绿。
- 新增或更新 `docs/plans/10-SAGE-V4.1.md`，记录实际落地方案、测试结果和已知后续项。

## 13. 开发注意事项

- Pydantic 使用 v2 写法：`model_dump()`，不要用 v1 风格 `dict()` 作为主路径。
- mypy 是 strict，新增文件必须有完整类型标注。
- typed events 的新增字段可以多，旧字段不能随便改名。
- `created_at` 建议统一使用 `core.coding.workspace.now()`。
- 不要让 `turn_started` / `turn_finished` 与现有 `SessionEventBus` 产生重复副作用；如果同时用于 trace 和 bus，要明确只 append 一次 trace。
- approval wait 仍要避免阻塞 event loop。
- 前端拆分以“行为不变”为第一优先级，不要顺手重做 UI。
- 如果某个 phase 出现大面积测试震荡，先回退到上一 phase，不要继续叠改。

## 14. 给开发 Agent 的简短执行指令

你要实现 Sage v4.1 Runtime Contract。请先读：

1. `docs/plans/08-SAGE-V3.md`
2. `docs/superpowers/specs/2026-07-08-sage-v4-hermes-runtime-contract-design.md`
3. 本文件
4. `core/coding/context_manager.py`
5. `core/coding/engine.py`
6. `core/coding/runtime.py`
7. `frontend/src/stores/coding.ts`

按 Phase 0-5 顺序开发。每个 phase 先写或更新测试，再实现。不要改旅游侧代码。不要改变现有 API URL。保持 UI 行为不变。最终必须跑全量后端检查、前端测试和前端 build，并把结果写入 `docs/plans/10-SAGE-V4.1.md`。
