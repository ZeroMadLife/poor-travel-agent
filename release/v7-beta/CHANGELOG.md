# Sage v7-beta Change Log

## v0.7.0-beta - 个人 AI 学习伴侣首版

Sage 从 Web Coding Agent 重定位为 **Personal AI Learning Companion**，并完成 DeerFlow 2.x Harness 兼容迁移、Knowledge Platform、受限 Research 子代理、持久 Timeline 与中文工作台。本版面向群友试用，不保证生产稳定。

### 产品定位

- **不是**：另一个通用 ChatGPT/Claude Code 克隆
- **是**：连接个人项目、笔记、文档，通过检索 + 对话 + 实践 + 引用持续形成知识资产的个人助手
- Coding Runtime 不删除，降级为 Practice Engine（源码阅读、代码实验、测试验证）

### Architecture

#### DeerFlow Harness 兼容迁移（Wave 0-5）

- Python 3.12 + LangChain/LangGraph 1.x 基线（`1aa80de`）
- 删除无生产入口的 Mem0/Qdrant/sentence-transformers 具体实现（`f5e165a`）
- 建立可独立安装的 `packages/sage_harness` 深模块包
- 应用中立 Ports + AST 依赖防火墙（`sage_harness` 不能 import `api.*`/Vue/Knowledge 具体存储）
- `SageThreadState` reducer + SQLite checkpointer + 22 个 `AgentMiddleware` 组合链
- runtime profile 双轨：`legacy`（XML Engine）+ `deerflow_v2`（LangGraph `create_agent` 原生 tool calling）
- Draft PR #8 覆盖 Wave 0-5；`deerflow_v2` 默认 gate 保持关闭

#### 22 个 Middleware 链

固定顺序，每个声明 hook / state channel / fail mode / timeline event / 相邻顺序测试：

1. InputSanitization → 2. ToolOutputBudget → 3. RemoteContentSanitization →
4. ThreadContext → 5. Sandbox → 6. DanglingToolCall → 7. ProviderError →
8. SagePolicy → 9. ApprovalInterrupt → 10. ReadBeforeWrite →
11. ToolProgress → 12. ToolError → 13. DurableContext → 14. Summarization →
15. Todo → 16. Memory → 17. DeferredTool → 18. SubagentLimit →
19. LoopDetection → 20. TokenBudget → 21. TerminalResponse → 22. Clarification

权限/审批/路径/owner/revision 必须 fail-closed；遥测/标题/非关键摘要可降级但必须留错误事件。

#### Harness 2.6 受限子代理

- **H2.6A Research 子代理**（`97a4431`，PR #40）：固定 `research` profile，只允许本地只读 + Knowledge Search + Web Search + 安全 Web Fetch；预算 24000 tokens / 16 steps / 180s；child transcript/tool args/网页正文不进父 timeline
- **H2.6B1 Research 并行预算**（`733b7ad`，PR #43）：多个 Research child 共享总预算，父取消传播取消
- **H2.6B2 Evidence Bundle 受限综合**（`e1c0ef1`，PR #46）：`EvidenceBundlePort` 只解析服务端生成的 Knowledge/Web/Fetch 成功结果；Synthesize profile 唯一工具 `read_evidence_bundle`，无网络/文件/Shell/写入/递归委派能力；必须成功读取非空 Bundle 否则 fail-closed
- **H2.6C Practice 子代理**（`a2b8f04`）：受限 Practice profile 产生结构化 Mastery Evidence 候选

#### Knowledge Platform

- `KnowledgeWorkspace` / `KnowledgeSource` / `KnowledgePage` / `KnowledgeRevision` 持久模型
- LLM Wiki 式 Markdown 产物 + 版本管理 + `proposals/` 审阅
- PostgreSQL 全文检索 + pgvector + RRF 混合检索（不引入 Elasticsearch/Milvus/Neo4j）
- 引用带 citation + Knowledge page/source revision + Web canonical URL/content hash
- 知识源提案（`KnowledgeSourceProposal` 状态机：pending/approved/rejected）
- 异步 PDF 解析队列（`codex/feat-h2-5b2-async-document-parsing`）
- 安全网页抓取与私有证据归档（`codex/feat-h2-5b1-safe-fetch-artifact`）

#### 持久 Timeline 与运行重连（V6.9 继承）

- `SessionEventJournal` SQLite 持久化 + `sequence` 全局递增 + `event_id` 幂等
- `RunCoordinator` 服务端持有 run，WebSocket 断开 ≠ 取消
- Timeline REST 分页 + WebSocket `after=N` 先重放后订阅（无竞态窗口）
- `recover_interrupted_runs`：进程重启后中断的 run 标记 `interrupted`（retryable），不伪造自动恢复
- fencing token 防止旧操作覆盖新状态
- persist-then-push：事件先进 SQLite 再推 WebSocket

#### V7.0 云控制面

- GitHub OAuth + PKCE S256 + HMAC state + 5 分钟 TTL + 浏览器绑定 cookie
- HttpOnly SameSite=Lax session（只存 SHA-256 hash）
- GitHub access token AES-GCM 加密存储
- Project / Workspace ownership 元数据
- 邀请码原子单次消费
- 生产环境 fail-closed：缺 secret/HTTPS/dev-login 误开启时拒绝

### Features

- 中文 Coding Workbench：左侧 session 栏、中间 `CodingMessageTurn` 时间线、右侧 Inspector（文件/变更/运行/记忆四 tab）
- 响应式布局：≥1280px 三栏 / 960-1279px inspector overlay / <960px 全屏 sheet
- URL 深链接 `/coding/session/:id`
- 滚动锚点恢复（切换会话回来看之前的位置）
- 父子 Run Trace 折叠展示
- 工具过程可折叠（运行中自动展开，参数+结果 JSON/文本高亮）
- 代码块语言标签 + Highlight.js + 复制按钮
- `/assistant` 首页（today + composer + 示例 prompt + 项目/对话摘要）
- 模型目录 TOML 配置（context window / output reserve / reasoning modes 单一服务端源）
- Provider 用量与 reasoning 状态
- Context 压力指示器（real token / effective window，非固定 60000 字符）
- 飞书 cc-connect 开发链路（与产品机器人分离）

### Bug Fixes

- lease 在 GeneratorExit 时不释放 → 外层 `try/finally` 清理 `active_run_id`
- Stop 不绑 run_id 误停新 run → `request_stop(run_id=...)` 校验
- Diff 跟随 symlink → `_scan_workspace` 跳过
- Diff 大文件只看大小 → 全文件 hash
- 切换会话回来工具调用消失 → Timeline 投影 + event_id 去重
- 前端固定 60000 字符 ring → 后端 `context_usage_updated` 真实 token
- `README.md` 误识别为外链 → 禁用模糊域名识别
- 工具缺参直接进入 approval/执行 → schema 预检查 + retry（最多 2 次纠正）
- 批量工具跨 workspace 边界 → 整体检查
- 复合验证命令 `python3 --version; pwd; ls -la` 被误拒 → 不放松危险命令检测的前提下放行
- 暗色模式 Teleport 弹窗白底 → 统一 `--sage-*` token
- 旧测试期望 `role/content` → 事件包络统一 `payload.type`
- 配置测试受开发机 `OPENAI_API_KEY` 污染 → 隔离
- owner isolation 测试隐式回退 PostgreSQL → 显式 SQLite
- Loop 无效 Worker 输出累积失败 → 严格重试（`21cc88a`）

### Defaults & DX

- Python: 3.11 → 3.12
- LangChain/LangGraph: 0.3 → 1.x
- runtime profile 默认：`legacy`（历史 session 不迁移）
- Context budget: 字符 → token
- 单 run 默认上限：50 steps
- Research child：24000 tokens / 16 steps / 180s
- 前端默认暗色模式 + 立即持久化
- 模型目录 `config/coding_models.toml`（DeepSeek Flash/Pro 显式 1M 窗口 + 64K 输出预留）
- `SAGE_CODING_MODELS_FILE` 部署路径覆盖
- `greenlet==3.5.3` 显式固定（SQLAlchemy async 依赖）

### Tests

- 后端：1644 passed（V7.5 + H2.6B2 基线）
- 前端：436 tests passed / 59 files
- mypy：264 source files 通过
- ruff：全仓通过
- GitHub Actions：`backend-quality` / `frontend-quality` / `python` 全绿
- 私有 Canary CI/CD + 可用性守护
- Benchmark：deterministic scenarios（信息性，非 CI 硬门禁）

### 部署

- Docker Compose + GitHub Actions + 单台 VPS（不依赖 Kubernetes）
- 国内 Debian/PyPI 镜像加速
- 反向代理 + HTTPS + 健康检查 + 备份 + 回滚
- 私有 Canary：`docs/runbooks/09-Sage私有Canary部署.md` / `10-Sage本地CI-CD与Canary可用性.md`

### Known Limitations

- 审批仍同进程 `ApprovalManager`，真正 LangGraph durable interrupt + 服务端重建 decision + 重启恢复未实现
- Container Sandbox 未在目标服务器真实验证
- MCP OAuth、跨实例恢复、完整 transport 兼容未完成
- legacy/v2 对等矩阵未完成
- `deerflow_v2` 默认 gate 关闭
- 首次进入没有 onboarding 引导（群友试用前必须补）
- 知识源导入前端入口不显式
- Loop Engineer 未启用（设计完成，门禁未通过）
- Dream 自动反思默认关闭
- AST 知识图谱 / Local Companion / 公网硬化留 V8

### 升级路径

- 旧 session 默认 `legacy` runtime，不迁移
- `dev/sage-v7` 领先 `main` 72 个 commit
- 不直接 merge `main`，需先完成对等矩阵 + 浏览器 E2E + 服务器隔离 smoke
- 用户数据兼容：durable timeline / transcript / memory store 向后兼容

### Breaking Changes

- Python 最低版本 3.12
- LangChain/LangGraph 1.x（不再兼容 0.3）
- 删除 Mem0/Qdrant/sentence-transformers 发布依赖
- `core/memory/mem0_factory.py` / `core/memory/long_term.py` / `scripts/demo_memory.py` 已删除
- 旅行图保留但只作为 domain skill，不再作为产品主线
