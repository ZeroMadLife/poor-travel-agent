# Sage v7-beta Review Pack

## Project Pitch

Sage 是一个 Web 形态的 Personal AI Learning Companion。它连接用户的 GitHub 项目、Obsidian 笔记、文档和外部资料，通过检索、对话、实践、验证、复盘与人工批准持续形成个人知识资产。

不同于通用 ChatGPT/Claude，Sage 的差异化在于：**知道你的项目和笔记，回答基于你自己的材料，带可验证引用**。Coding Runtime 保留但降级为 Practice Engine。

本版面向群友试用，不保证生产稳定。

## Architecture Map

### 顶层分层

```
Vue Assistant Shell / Coding Workbench
  ↓ WebSocket / REST
FastAPI App (api/)
  ↓
Harness Runtime Adapter (core/harness/)
  ↓
sage_harness package (packages/sage_harness/)
  ├── agents/ - create_agent + factory + SageThreadState
  ├── runtime/ - RunManager + checkpointer + events
  ├── middleware/ - 22 个 AgentMiddleware 组合链
  ├── tools/ - registry + metadata + adapters
  ├── sandbox/ - base + local
  ├── mcp/ - manager + deferred
  ├── subagents/ - registry + executor + events
  ├── context/ - durable + summarization
  └── memory/ - port + tools
  ↓
LangChain create_agent + LangGraph
  ↓
Sage Business Stores
  ├── SessionEventJournal (SQLite timeline)
  ├── TranscriptStore (SQLite canonical)
  ├── CompactionStore (SQLite + HMAC)
  ├── MemoryStore (revisioned + proposal)
  ├── KnowledgeStore (Wiki + RAG + citation + revision)
  ├── RunStore (trace.jsonl + diff.json)
  └── ArtifactStore (tool-results / diffs / 长输出)
```

### 三层事实边界（不可混淆）

| 存储 | 事实源职责 | 不可做 |
| --- | --- | --- |
| LangGraph checkpointer | Agent 执行状态、graph resume | 取代 Sage timeline 审计 |
| Sage SessionEventJournal | 用户可见事件、replay、UI 投影 | 保存业务对象完整内容 |
| TranscriptStore | 规范化消息查询、历史兼容 | 被压缩修改 |
| KnowledgeStore | Wiki/Source/Revision/Citation | 被 Agent 直接写入（必须走 proposal） |
| MemoryStore | 用户确认的稳定事实 | 接受模型自动持久化 |
| RunStore | run trace + diff + summary | 取代 timeline 终态 |
| ArtifactStore | 长输出/文件/生成物 | 进入 model context 全文 |

存储间通过稳定引用关联，不互相复制完整对象。

### Runtime Profile 双轨

```
legacy       CodingRuntime + XML <tool>/<final> Engine
deerflow_v2  sage_harness + LangGraph create_agent + 原生 tool calling
```

- session 创建时服务端选择并持久化
- run 开始后不可切换
- 历史 session 解释为 `legacy`，不静默迁移
- `deerflow_v2` 默认 gate 关闭，通过对等矩阵后才切

### 22 个 Middleware 链（固定顺序）

```
InputSanitization -> ToolOutputBudget -> RemoteContentSanitization
  -> ThreadContext -> Sandbox -> DanglingToolCall -> ProviderError
  -> SagePolicy -> ApprovalInterrupt -> ReadBeforeWrite
  -> ToolProgress -> ToolError -> DurableContext -> Summarization
  -> Todo -> Memory -> DeferredTool -> SubagentLimit
  -> LoopDetection -> TokenBudget -> TerminalResponse -> Clarification
```

fail-closed：权限/审批/路径/owner/revision
fail-open（必须留错误事件）：遥测/标题/非关键摘要

### 受限子代理 Capability

```
父 Agent
  ↓ task 工具委派（受 SubagentLimit 限制）
Research child（固定 profile）
  ├── 工具：本地只读 + Knowledge Search + Web Search + 安全 Web Fetch
  ├── 预算：24000 tokens / 16 steps / 180s
  └── 结果以受限 ToolMessage 返回
  ↓
EvidenceBundlePort（只解析服务端成功结果）
  ↓ 去重 + token budget 截断
Synthesize profile（唯一工具 read_evidence_bundle）
  ↓ 必须成功读取非空 Bundle，否则 fail-closed
父 timeline 收到综合结果
```

父 timeline 只看到：subagent_progress / brief / result ref / evidence refs。child transcript / tool args / 网页正文不进父 timeline。

### 知识平台数据流

```
KnowledgeSource 提案
  ↓ 用户审阅批准
摄取 Job（异步队列 + 租约 + 重试 + 恢复）
  ↓
原始来源归档（raw/sources/，不可变）
  ↓ 分块 + embedding
PostgreSQL 全文检索 + pgvector + RRF
  ↓
检索结果带 citation + Knowledge page/source revision
  ↓
模型回答带可点击引用
  ↓
Wiki 更新 proposal（用户审阅后写入 pages/）
```

### 持久 Timeline 与重连

```
WebSocket 接入
  ↓
RunCoordinator 持有 run（不绑 WebSocket）
  ↓
每个事件:
  1. SessionEventJournal.append (SQLite, sequence + event_id 幂等)
  2. broadcast 到 subscribers
  3. WebSocket 推送
  ↓
断线重连:
  GET /timeline?after=<last_sequence>  ← REST 重放
  WebSocket /stream?after=<sequence>    ← 先重放后订阅（无竞态）
  ↓
进程重启:
  recover_interrupted_runs -> 标记 interrupted（retryable）
  不伪造自动恢复
```

## Harness Boundaries

### sage_harness 包依赖防火墙

```
api / app
  -> core adapters
      -> sage_harness ports
          -> LangChain / LangGraph

sage_harness -X-> api
sage_harness -X-> Vue
sage_harness -X-> Knowledge concrete store
```

AST 边界测试强制执行（`tests/harness/test_package_boundary.py`）。

### Sage Policy 五道门（V6 继承）

```
① PermissionChecker - "有没有权做"（plan_mode / write_scope / approval_policy）
② ToolPolicyChecker - "做法合不合理"（read-before-write / shell 分类）
③ ApprovalManager - "需要用户确认"（11 个危险模式匹配）
④ RegisteredTool.execute - "真正执行"（ThreadPoolExecutor + 超时）
⑤ WorkspaceContext - "路径安全"（O_NOFOLLOW + hardlink 检测 + inode 验证）
```

## Sample Run Artifact List

```
.coding/
  sessions/<session_id>.json              # 会话状态（history/modes/todos/activated_tools）
  evidence/<session_id>/
    transcript.sqlite3                    # canonical 消息记录（append-only）
    timeline.sqlite3                      # SessionEventJournal（事件审计源）
    compactions/<compaction_id>.json      # 压缩 checkpoint
    runs/<run_id>/
      trace.jsonl                          # run 事件序列
      diff.json                            # workspace diff
      tool-results/<tool_call_id>.txt      # 大工具结果归档
  memory/
    workspaces/<workspace_id>/
      state.json                           # revisioned memory facts
      MEMORY.md                            # 人类可读索引（可重建）
      project-conventions.md / decisions.md
      proposals/<proposal_id>.json         # Dream 提案
  knowledge/
    workspaces/<workspace_id>/
      raw/sources/                         # 不可变来源
      pages/                               # LLM Wiki Markdown
      proposals/                           # Wiki 更新提案
      index.md / log.md / schema.md
```

## Benchmark Evidence

- 后端定向：H2.6B2 Evidence/Subagent/State `46 passed`，Harness/Coding/API 关联 `315 passed`
- 后端全量：`1644 passed`
- 前端：`59 files / 436 tests passed`
- mypy：`264 source files` 无错误
- ruff：全仓通过
- GitHub CI：`backend-quality` / `frontend-quality` / `python` 全绿
- PostgreSQL 隔离回归：`DATABASE_URL` 指向不可达端口时 `test_coding_surface_context.py` 仍 `6 passed`
- Benchmark：deterministic scenarios（信息性，非 CI 硬门禁）

## Security Review

### Critical（已关闭）

- LangChain 0.3 与 1.x 不能混装 -> Wave 0 独立门禁
- checkpoint 与 timeline 不能产生矛盾终态 -> 适配器 + 恢复器测试
- 客户端 approval payload 不能直接送 graph -> 服务端重建 + args digest 校验

### High（已关闭）

- 中间件顺序错误绕过审批 -> 组合测试锁定
- 子代理继承全部工具 -> 默认最小 capability
- 自动记忆持久化模型错误 -> proposal/evidence gate
- Local Sandbox 生产环境 = host code execution -> Container Sandbox

### Medium（部分关闭）

- checkpoint 和 timeline 双写部分成功 -> 幂等 event ID + 恢复补偿
- 大量 Tool schema 增加首 token 延迟 -> deferred tool search
- 书籍示例与 upstream 漂移 -> 固定 commit + provenance

### 群友试用前必须验证

- A 用户看不到 B 用户任何数据（session/memory/file/workspace）
- 单用户资源上限不跑死服务器
- 三大浏览器核心流程不崩
- 公网 HTTPS 24h 稳定

## Verified Source Commits

- DeerFlow Harness 迁移 Draft PR：`344c1d6`（PR #8）
- H2.6A Research 子代理：`97a4431`（PR #40，merge `0035791`）
- H2.6B1 Research 并行预算：`733b7ad`（PR #43，merge `25df68b`）
- H2.6B2 Evidence 受限综合：`e1c0ef1`（PR #46，merge `468bacf`）
- H2.6C Practice 子代理：`a2b8f04`
- V7.0 GitHub OAuth：`f261787` / `61a6c6a`
- 目标驱动产品壳层：`4479ad2`
- 本地联调根目录 HEAD：`4479ad2`（截至 2026-07-19）

## 下一阶段边界

1. **群友试用前补丁**：onboarding 引导 / 知识源导入入口 / 多用户隔离验证 / 三浏览器兼容
2. **Approval Resume**：LangGraph durable interrupt + 服务端重建 decision + 重启恢复
3. **Container Sandbox 服务器验证**：Ubuntu/Docker 真实镜像/CPU/内存/PID/网络/workspace mount
4. **对等矩阵**：legacy vs `deerflow_v2` 任务完成率/工具成功率/P95 延迟/policy compliance
5. **MCP OAuth** + 跨实例恢复 + 完整 transport 兼容
6. **Loop Engineer 启用门禁**：`gh` CLI + required checks + 分支保护
7. **V8**：Local Companion + Code RAG + AST 知识图谱 + 公网硬化
