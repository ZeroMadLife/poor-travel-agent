# Codex Goal：Phase 6.1 — 框架抽象层（Runtime + Skill 重构）

## 任务类型
goal 执行（自驱完成，直到验收通过）

## 背景

TourSwarm 原定位是"旅游助手"，现重定位为"个人 Agent 框架，旅游为首个落地场景"。
完整设计文档见仓库内：`docs/superpowers/specs/2026-07-05-agent-framework-repositioning-design.md`

本次 goal 只执行 **Phase 6.1：框架抽象层**——把现有旅游特化的主 Agent 代码切成"通用 AgentRuntime + 可插拔 Skill"，为后续 coding Skill / 框架级 RAG / 外部 Agent 接入打地基。

**核心约束：旅游侧行为完全不变，现有测试全绿。这是回归红线。**

## 现有代码形状（改动前先读这些文件）

| 文件 | 现状 | 本次改动 |
|------|------|---------|
| `agents/react_agent.py` | 模块级常量 `AGENT_SYSTEM_PROMPT` 硬编码旅游人设；`TourAgent.__init__(llm, tools: dict, ...)` 接收工具字典 | system_prompt 和 tools 改成从 Skill 读入；TourAgent 改名/抽象为 AgentRuntime |
| `core/verifier.py` | 函数 `verify_itinerary(itinerary, dates, budget_total, weather_info)` | 抽象成 `Verifier` 协议/接口，现有函数包装成 `ItineraryVerifier` 实现 |
| `core/memory/long_term.py` | `LongTermMemory(mem0_client, user_id)`，仅按 user_id 隔离 | 加 `scope` 元数据（`session` / `skill:{name}` / `user`），search 时按 scope 过滤 |
| `core/memory/short_term.py` | Redis 短期记忆，按 session | 不改（已天然 session 隔离） |
| `agents/itinerary_tool.py` | `generate_itinerary` 工具，包装 LangGraph 多Agent图 | 不改（作为 travel-planning Skill 的 sub_agent_graph） |
| `mcp_servers/registry.py` | `build_mcp_config` 返回 amap/weather/scenic 三个 stdio server | 不改（旅游 MCP 原样保留） |
| `api/services/chat_runner.py` | 组装 TourAgent + tools 的入口 | 改成按 session 绑定 Skill，传给 AgentRuntime |
| `core/skill.py` | 不存在 | **新增**：Skill 数据结构 + 注册表 |

## 交付物

### 1. `core/skill.py`（新增）

定义 Skill 数据结构，至少包含：

```python
class Skill(BaseModel):
    name: str                          # "travel-planning"
    system_prompt: str                 # 该 skill 的人设
    tools: list[ToolSpec]              # 该 skill 可用的工具集
    sub_agent_graph: Any | None        # 复杂任务多Agent编排（旅游有，coding 无）
    verifier: Verifier | None          # 领域验证器（旅游有，coding 无）
    memory_config: MemoryConfig        # 记忆策略
    knowledge_sources: list[KnowledgeSource]  # RAG 知识源（本阶段留空 list 即可）
```

配套一个 `SkillRegistry`，能按 name 注册和查找 Skill。
本阶段只注册一个 Skill：`travel-planning`，把现有 `AGENT_SYSTEM_PROMPT`、旅游工具集、`ItineraryVerifier`、`generate_itinerary` sub-graph 打包进去。

### 2. `agents/react_agent.py` → AgentRuntime 重构

- `TourAgent` 重命名/抽象为 `AgentRuntime`（保留旧名做 alias 以减少改动也可）
- `__init__` 接收 `Skill`（或 skill_name + SkillRegistry），从中读 system_prompt 和 tools
- ReAct 循环逻辑**不动**，只是 prompt 和 tools 来源从硬编码变成 Skill 注入
- 如果 Skill 带 sub_agent_graph，对应工具（`generate_itinerary`）照旧注册
- 如果 Skill 带 verifier，输出前过验证器（旅游侧保持现有行为）

### 3. `core/verifier.py` 抽象成 Verifier 接口

- 定义 `Verifier` 协议（Protocol 或 ABC），方法签名类似 `verify(self, output, context) -> VerificationResult`
- 现有 `verify_itinerary` 函数包装成 `ItineraryVerifier(Verifier)` 类
- `VerificationResult` / `VerificationIssue` 保留不变（API 响应和 eval 依赖它们）
- 旅游侧行为不变

### 4. `core/memory/long_term.py` 三层记忆隔离

- `LongTermMemory` 的 `add` 和 `search` 增加 `scope` 参数
- scope 取值：`"session:{id}"` / `"skill:{name}"` / `"user:{id}"`
- 存储时把 scope 作为 Mem0 的 metadata 写入
- 检索时按 scope 过滤（Mem0 的 search 支持 metadata 过滤）
- **不破坏现有调用**：现有只传 `user_id` 的调用保持向后兼容（默认 scope = `user:{id}`）
- 旅游侧"喜欢海鲜"这类偏好，新存时打 `skill:travel-planning` 标签

### 5. `api/services/chat_runner.py` 接入 Skill

- 启动时从 SkillRegistry 取 `travel-planning` Skill
- 传给 AgentRuntime 构造
- session 首次创建时绑定 skill_name（本阶段固定 travel-planning，后续支持切换）

### 6. 测试

- 现有 51 个测试文件**必须全绿**（`bash scripts/check.sh`）
- 新增 `tests/core/test_skill.py`：Skill 注册/查找、AgentRuntime 从 Skill 读 prompt/tools
- 新增 `tests/core/test_verifier_interface.py`：ItineraryVerifier 实现 Verifier 接口，行为与原 `verify_itinerary` 一致
- 新增 `tests/core/test_memory_scope.py`：三层 scope 隔离（skill 级记忆不跨 skill 可见，user 级全局可见）

## 验收标准（必须全部满足）

1. `bash scripts/check.sh` 全绿，不破坏任何现有测试
2. 旅游侧行为完全不变：用 README 里的推荐联调输入（"帮我规划杭州2日游预算500元，喜欢美食和自然风光"）跑通，输出与重构前一致
3. `core/skill.py` 存在，`travel-planning` Skill 已注册
4. `AgentRuntime` 从 Skill 读 prompt/tools，不再有旅游硬编码
5. `Verifier` 接口存在，`ItineraryVerifier` 是其实现
6. `LongTermMemory` 支持 scope 参数，三层隔离测试通过
7. 新增测试覆盖 Skill / Verifier 接口 / 记忆 scope

## 不要做的事

- 不要动 `agents/itinerary_tool.py`、`mcp_servers/*`、`agents/graph.py` 等 Skill 内部实现
- 不要做 coding Skill（那是 Phase 6.2）
- 不要做 RAG / retrieve 工具（那是 Phase 6.3）
- 不要做 Dify/Coze 适配器（那是 Phase 6.4）
- 不要改前端（Skill 切换 UI 是 Phase 6.2 的事）
- 不要为了"通用"而过度抽象——本阶段只有一个 Skill，抽象到能支撑第二个即可

## 执行顺序建议

1. 先读 `docs/superpowers/specs/2026-07-05-agent-framework-repositioning-design.md` 第 4 节（AgentRuntime 核心抽象）
2. 先写 `core/skill.py` + `Verifier` 接口（纯新增，不破坏现有）
3. 重构 `react_agent.py` → AgentRuntime，跑回归测试
4. 加记忆 scope，跑回归测试
5. 改 `chat_runner.py` 接入 Skill，跑回归测试
6. 写新测试，跑全量 `scripts/check.sh`
7. 手动联调验证旅游侧行为不变

## 完成标志

`bash scripts/check.sh` 全绿 + 旅游侧手动联调通过 + 所有交付物存在且符合上述描述。

完成后在 commit message 里标注 `phase-6.1`，并在 `docs/plans/` 下新建 `06.1-PHASE6.1-FRAMEWORK-ABSTRACTION.md` 记录实际改动和验收结果。
