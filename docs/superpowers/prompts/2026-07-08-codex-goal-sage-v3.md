# Codex Goal：Sage v3 - 架构重构（Prompt Caching + Approval + 工具系统 + 前后端交互）

## 任务类型
goal 执行（自驱完成，直到验收通过）

---

## 背景

项目代号 **Sage**，是一个网页端个人 Coding 助手，位于 `/Users/zeromadlife/Desktop/tour-agent`。已完成 v1（Pico v3 runtime 移植）和 v2（前端三栏布局 + Skills 系统）。

本次 v3 要参照 **Hermes Agent** 和 **Hermes WebUI** 的设计，对后端架构做四个方向的重构。两个 Hermes 仓库已经 clone 到本地：
- 后端参考：`/Users/zeromadlife/Desktop/hermes-study/hermes-agent`
- 前端参考：`/Users/zeromadlife/Desktop/hermes-study/hermes-webui`

**先读 `docs/superpowers/specs/2026-07-07-sage-v2-design.md` 了解现有架构，再动手。**

## 两条红线

1. **旅游侧代码不动**：`agents/`、`mcp_servers/amap|weather|scenic`、`core/verifier.py`、`evals/` 等全部不改
2. **现有测试不破**：`bash scripts/check.sh` 必须 297 passed，`cd frontend && npm run test -- --run` 必须全绿

## 第零步：跑 graphify 梳理现有架构

```bash
cd /Users/zeromadlife/Desktop/tour-agent
graphify .
```

读 `graphify-out/graph.json` 和 `graphify-out/GRAPH_REPORT.md`，理解现有模块依赖关系。后续重构时参考这个图，确保不引入循环依赖。

---

## 方向一：ContextManager 重构 - Prompt Caching 策略

### 问题

当前 `core/coding/context_manager.py` 每轮 rebuild prompt（prefix+tools+history+current），DeepSeek/OpenAI 的隐式前缀缓存全部失效，浪费 token 和延迟。

### 参考（Hermes 源码）

- `/Users/zeromadlife/Desktop/hermes-study/hermes-agent/agent/system_prompt.py` - 三层组装 + 单次构建 + invalidate（核心范本，重点读 `build_system_prompt_parts()` 和 `invalidate_system_prompt()`）
- `/Users/zeromadlife/Desktop/hermes-study/hermes-agent/agent/prompt_caching.py` - 显式 cache_control breakpoint（120 行纯函数，未来接 Anthropic 时用，本轮先不移植）
- `/Users/zeromadlife/Desktop/hermes-study/hermes-agent/agent/conversation_loop.py:840-946` - 每轮组装 + 消息规范化
- `/Users/zeromadlife/Desktop/hermes-study/hermes-agent/agent/conversation_compression.py:708-710` - 压缩后 invalidate+重建

### 要做的事

改造 `core/coding/context_manager.py`：

1. **system prompt 单次构建 + 缓存**
   - 加 `_cached_system_prompt: str | None` 和 `_system_prompt_dirty: bool`
   - `build_system_prompt_once()` 方法：dirty=False 时直接返回缓存，True 时重建
   - `invalidate_system_prompt()` 方法：设 dirty=True，下轮重建

2. **三层拆分**
   - **stable**：Sage 身份 + 工具指引 + skills 索引（进程生命周期内不变）
   - **context**：项目级上下文（session 内不变）
   - **volatile**：memory 快照 + 时间戳（session 内不变，但跨 session 变）
   - **时间戳用日期精度**（`date.today().isoformat()`），不用分钟/秒，保证一天内 byte-stable

3. **消息规范化（bit-perfect 前缀）**
   - 在 `build()` 返回的 prompt 上做规范化：str content `.strip()`
   - 保证同一 history 每轮产出相同前缀

4. **skill/命令注入走 user message**
   - `api/coding.py` 的 slash 命令处理已经把 skill.render() 作为 user_message 传给 engine，确认这条路径不破坏 system prompt 缓存

5. **压缩路径接入 cache 失效**
   - `core/coding/compact.py` 压缩后调 `context_manager.invalidate_system_prompt()`
   - 下一轮重建 system prompt（趁 memory 刷新）

### 验收
- `test_context_compact.py` 现有测试全过
- 新增测试：system prompt 跨轮缓存（同一 session 两轮 build 返回相同字符串）、invalidate 后重建、时间戳日期精度
- 手动确认：同一 session 多轮对话时，context_manager 不每轮 rebuild system prompt

---

## 方向二：权限 Approval 系统 - 工具权限 + 并行 + 安全异步策略

### 问题

当前 `core/coding/permissions.py` 的 `PermissionChecker` 有 approval_policy（auto/ask/never），但 auto 模式下 risky 工具直接执行，无暂停机制，无前端 approval UI。

### 参考（Hermes 源码）

- `/Users/zeromadlife/Desktop/hermes-study/hermes-agent/tools/approval.py` - 危险命令检测 + 审批编排（核心，重点读 `_await_gateway_decision`、`run_approval_gate`、`_ApprovalEntry`）
- `/Users/zeromadlife/Desktop/hermes-study/hermes-webui/static/messages.js:6577-6735` - 前端 approval 逻辑
- `/Users/zeromadlife/Desktop/hermes-study/hermes-webui/static/index.html:487-522` - approval 卡片 DOM

### 要做的事

#### 2.1 后端：Approval 阻塞机制

新增 `core/coding/approval.py`：

```python
@dataclass
class ApprovalEntry:
    approval_id: str
    session_id: str
    tool: str
    args: dict
    description: str        # 为什么需要审批
    pattern_key: str        # 危险模式标识
    event: threading.Event
    result: str | None      # "once" / "session" / "always" / "deny"

class ApprovalManager:
    """Session 级审批队列和阻塞机制。"""
    def submit(self, session_id, tool, args, description, pattern_key) -> ApprovalEntry
    def resolve(self, session_id, approval_id, choice) -> bool
    def pending(self, session_id) -> dict | None
    def is_session_approved(self, session_id, pattern_key) -> bool
```

核心机制（照搬 Hermes）：
- `submit()` 创建 `ApprovalEntry`，append 到 `_queues[session_id]`
- `submit()` 返回后，调用方在 `entry.event.wait(timeout=300)` 阻塞
- `resolve()` 设 `entry.result` + `entry.event.set()` 唤醒
- 每 1s 检查超时和中断
- **关键**：阻塞期间不能卡死 WebSocket 事件流

**异步策略**：Sage 的 engine 是 async generator。approval 阻塞要用 `asyncio.to_thread(entry.event.wait, timeout=1.0)` 桥接，不阻塞 event loop。具体：
- engine yield `approval_required` 事件后，`await asyncio.to_thread(...)` 等待结果
- WebSocket 继续可收发（用户通过另一个 WebSocket 消息 respond）

#### 2.2 危险命令检测

新增 `core/coding/approval.py` 里的 `DANGEROUS_PATTERNS`（精简版，从 Hermes 的 47 条裁剪到 ~15 条最常用的）：
- `rm -r` / `rm -rf`
- `git reset --hard`
- `git push --force`
- `chmod 777`
- `curl.*|.*sh` / `wget.*|.*sh`
- `sudo`
- 写入 `/etc/` 或 `~/.ssh/`
- `docker compose down`
- `kill -9`

`check_dangerous_command(command) -> tuple[bool, str, str]`：返回 `(is_dangerous, description, pattern_key)`。

#### 2.3 PermissionChecker 接入

改造 `core/coding/permissions.py`：
- policy=auto 时，risky 工具直接执行（现有行为）
- policy=ask 时，risky 工具走 `ApprovalManager.submit()` -> 阻塞等待
- run_shell 工具额外检查 `check_dangerous_command()`
- session 级已批准的 pattern_key 不再问

#### 2.4 API 端点

在 `api/coding.py` 新增：

```
GET  /api/v1/coding/{session_id}/approval/pending   -> 队首 pending 审批
POST /api/v1/coding/{session_id}/approval/respond   -> {choice: "once"|"deny"|"session"|"always"}
```

WebSocket 事件流里新增 `approval_required` 事件类型。

#### 2.5 前端：Approval 卡片

新增 `frontend/src/components/CodingApprovalCard.vue`：
- 浮层卡片（固定在 composer 上方，非内联消息）
- 显示：工具名 + 参数 + 风险描述
- 两个按钮（MVP）：Allow once / Deny
- 点击后 `POST /approval/respond`
- 响应成功后卡片消失

在 `stores/coding.ts` 里加 approval 状态管理：
- 监听 WebSocket 的 `approval_required` 事件
- 轮询 `GET /approval/pending`（1.5s 间隔，thinking 时才轮询）

### 验收
- 新增 `tests/core/coding/test_approval.py`：submit/resolve/timeout/session_approved
- 新增 `tests/api/test_coding_approval.py`：pending/respond 端点
- policy=ask 时 risky 工具触发审批，前端显示卡片，respond 后继续执行
- policy=auto 时不触发审批（现有行为不变）
- 前端测试覆盖 approval 卡片交互

---

## 方向三：工具系统重构

### 问题

当前 `core/coding/tools/registry.py` 用手写 `TOOL_SPECS` dict，6 个核心工具还够用，但加上 todo/plan/worker 共 15 个工具时维护成本上升。工具执行是同步的，没有超时控制。

### 参考（Hermes 源码）

- `/Users/zeromadlife/Desktop/hermes-study/hermes-agent/tools/registry.py` - AST 扫描自动发现 + `check_fn` TTL 缓存
- `/Users/zeromadlife/Desktop/hermes-study/hermes-agent/toolsets.py` - toolset 分组
- `/Users/zeromadlife/Desktop/hermes-study/hermes-agent/tools/base.py` - 工具基类

### 要做的事

#### 3.1 工具注册改装饰器模式

改造 `core/coding/tools/registry.py`：
- 保留 `RegisteredTool` 和 `ToolResult`（不动）
- 新增 `@register_tool(name, description, risky, schema)` 装饰器
- 每个工具函数文件模块级调 `@register_tool`，不再集中写 dict
- `build_tool_registry()` 扫描 `core/coding/tools/` 下所有模块，收集注册的工0具

拆分工具到独立文件（当前全在 `registry.py`）：
```
core/coding/tools/
├── base.py           # RegisteredTool / ToolResult（不动）
├── schemas.py        # pydantic Args（不动）
├── registry.py       # 装饰器 + build_tool_registry（改）
├── file_tools.py     # list_files / read_file / search / write_file / patch_file
├── shell_tool.py     # run_shell
├── todo_tools.py     # todo_add / todo_update / todo_list
├── plan_tools.py     # enter_plan_mode / exit_plan_mode
├── agent_tools.py    # agent / send_message / task_stop
└── __init__.py
```

#### 3.2 工具执行超时

`run_shell` 已有 timeout 参数。其他工具加默认超时：
- `RegisteredTool.execute()` 加 `timeout` 参数（默认 30s）
- 用 `asyncio.wait_for` 或 `concurrent.futures` 包裹同步工具执行

#### 3.3 工具元数据增强

`RegisteredTool` 加字段：
- `category: str` - 工具分类（"file" / "shell" / "todo" / "plan" / "agent"）
- `requires_approval: bool` - 是否需要审批（risky=True 的默认 requires_approval=True）

### 验收
- 所有现有工具测试全过
- 新增测试：装饰器注册、工具发现、超时
- 工具拆分后 `build_tool_registry()` 返回相同工具集

---

## 方向四：前后端交互 - 对标 Hermes WebUI

### 问题

当前前端交互基础已有（三栏 + 文件树 + 工具折叠 + skills），但对比 Hermes WebUI 还有多个细节差距。

### 参考（Hermes WebUI 源码）

- `/Users/zeromadlife/Desktop/hermes-study/hermes-webui/static/ui.js` - 工具卡片 DOM / context 环 / 文件树渲染
- `/Users/zeromadlife/Desktop/hermes-study/hermes-webui/static/messages.js` - SSE 事件处理 / send() / approval 逻辑
- `/Users/zeromadlife/Desktop/hermes-study/hermes-webui/static/workspace.js` - 文件树懒加载 / git badge
- `/Users/zeromadlife/Desktop/hermes-study/hermes-webui/static/panels.js` - Skills/MCP 面板
- `/Users/zeromadlife/Desktop/hermes-study/hermes-webui/static/index.html` - 三栏布局 HTML

### 要做的事

#### 4.1 工具结果截断 + 智能断行

改造 `CodingToolActivity.vue`：
- 工具 result 超过 800 字符截断
- 优先在 `. ` / `\n` / `; ` 处断开
- "Show more" / "Show less" 切换
- diff 结果高亮（`+` 行绿 / `-` 行红）

#### 4.2 两阶段渲染防跳

改造 `CodingToolActivity.vue`：
- settled 那一帧强制 `keepOpen=true`（不折叠），nextTick 后再 collapse
- 避免折叠导致的几百 px 跳变

#### 4.3 文件树两层缓存

改造 `CodingFileTree.vue`：
- 加 `_dirCache`（目录条目缓存）+ `_expandedDirs`（Set）
- 展开目录时先查缓存，miss 再请求
- 代际号防竞态（`_treeGen`，请求返回时校验）

#### 4.4 context 环增强

改造 `CodingComposer.vue`：
- context 环加 tooltip（usage / tokens / budget）
- 超过 75% 显示 "压缩" 提示按钮

#### 4.5 Skills 面板分类折叠

改造 `CodingSidebar.vue`：
- skills 按 source 分类（builtin/user/project）
- 分类可折叠
- 加搜索框过滤

#### 4.6 工具调用时刷新文件树 + git

在 `stores/coding.ts` 里：
- `tool_result` 事件里如果是 write_file/patch_file/run_shell，触发 `loadFiles()` + `loadGitStatus()`
- 让文件树和 git badge 实时反映 agent 的改动

### 验收
- 前端测试全过
- 工具结果超长时截断 + Show more 可用
- 文件树展开目录有缓存（不重复请求）
- agent 改文件后文件树自动刷新

---

## 不要做的事

- 不要动旅游侧代码
- 不要移植 Hermes 的 provider profile 系统（复用现有 `core/llm.py`）
- 不要移植 Hermes 的 plugin 系统 / context engine ABC / memory provider ABC
- 不要移植 Hermes 的 CLI / TUI / gateway / cron / 20 个消息平台
- 不要移植 Hermes 的 sandbox/bubblewrap
- 不要做 Skill 自学习闭环 / Curator
- 不要改 `core/coding/engine.py` 的 async generator 核心循环（只改它调用的 context_manager）
- 不要改 `core/coding/workspace.py`（已经很完善）
- 不要用 vanilla JS（保持 Vue3 + Pinia）

## 执行顺序

```
第零步  graphify 梳理架构
   ↓
方向一  ContextManager prompt caching     ← P0，改动最小收益最大
   ↓
方向三  工具系统重构（装饰器 + 拆分）       ← 先重构工具，approval 才能接入
   ↓
方向二  Approval 系统                     ← 依赖方向三的工具元数据
   ↓
方向四  前后端交互增强                     ← 最后做体验优化
```

每完成一个方向，跑 `bash scripts/check.sh` + `cd frontend && npm run test -- --run`，绿了再下一方向。

## 完成标志

- `bash scripts/check.sh` 全绿（297+ passed）
- `cd frontend && npm run test -- --run` 全绿
- `cd frontend && npm run build` 通过
- graphify 产出更新到 `graphify-out/`
- commit message 标注 `sage-v3`
- `docs/plans/08-SAGE-V3.md` 记录落地
- 每个方向都有对应测试

## Hermes 源码阅读指引

Codex 执行时遇到不确定的设计决策，优先读 Hermes 源码对应的文件。关键对照表：

| 要解决的问题 | Hermes 参考文件 |
|---|---|
| system prompt 怎么缓存 | `hermes-agent/agent/system_prompt.py` |
| 消息规范化怎么搞 | `hermes-agent/agent/conversation_loop.py:915-946` |
| 压缩后怎么 invalidate | `hermes-agent/agent/conversation_compression.py:708-710` |
| approval 怎么阻塞 | `hermes-agent/tools/approval.py` 的 `_await_gateway_decision` |
| 危险命令怎么检测 | `hermes-agent/tools/approval.py` 的 `DANGEROUS_PATTERNS` |
| 工具怎么自注册 | `hermes-agent/tools/registry.py` 的 `discover_builtin_tools` |
| 前端工具卡怎么折 | `hermes-webui/static/ui.js` 的 `buildToolCard` |
| 前端 approval 卡 | `hermes-webui/static/messages.js:6577-6735` |
| 前端文件树缓存 | `hermes-webui/static/workspace.js` 的 `loadDir` |
| 前端 context 环 | `hermes-webui/static/ui.js:5854` 的 `_syncCtxIndicator` |
