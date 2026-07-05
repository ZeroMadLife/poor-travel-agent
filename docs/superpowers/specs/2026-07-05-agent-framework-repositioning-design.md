# TourSwarm 个人 Agent 框架重定位设计

> 日期：2026-07-05
> 状态：已与用户确认方向，待 spec 审阅
> 决策性质：产品方向 + 架构抽象层设计

---

## 1. 背景与问题

### 1.1 现状

TourSwarm 当前定位是"两段式智能旅游 Agent"。已完成 Phase 1–5：

- 3 个自研 MCP Server（高德/天气/景点）
- ReAct 主 Agent + `generate_itinerary` 包装 LangGraph 多Agent图
- Redis 短期记忆 + Mem0/Qdrant 长期记忆 + 上下文压缩
- 确定性验证器（时间/预算/空间/约束 4 重检查）
- Vue3 聊天界面 + FastAPI + WebSocket 流式输出
- 对话持久化 + 历史会话 + 口令验证多用户隔离

代码结构上，主 Agent（`agents/react_agent.py`）已经是一个通用的 ReAct 循环 + 工具调用 + 记忆 + 多Agent编排的框架雏形，旅游只是它当前装的 prompt 和工具集。

### 1.2 矛盾

用户在规划后续能力（技能系统、外接 Dify/Coze、大众点评知识接入、Agentic-RAG）时发现方向感混乱：这些能力听起来越来越像"通用 AI Coding 助手 / Chatbot 框架"，而非旅游垂直助手。本质是**叙事错位**——代码已经是通用 agent 框架的形状，但叙事还停留在"旅游助手"。

### 1.3 约束

- **作品集为主**：项目的首要目的是求职作品集。每做一件事都要能回答"这增加什么亮点"。
- **替换 Pico**：用户原本简历上的 Pico（通用 AI Coding 助手）要被本项目替换。TourSwarm 需要能覆盖 Pico 原本要讲的能力点。
- **沉没成本不浪费**：旅游侧已有的 MCP Server、多Agent图、验证器、记忆系统、eval 数据不重写。

---

## 2. 方案选择

讨论了三个方案：

| 方案 | 描述 | 结论 |
|------|------|------|
| A. 保持旅游特化 | 继续深扎旅游，TourSwarm 与 Pico 并存 | 与"替换 Pico"意愿冲突，且精力分散 |
| B. 推翻旅游重做 Coding 助手 | 放弃旅游场景，改造成 Pico 那样 | 沉没成本极大，且丢失旅游差异化亮点 |
| **C. 重定位叙事 + 补抽象层** | 代码不动方向，抽象出框架层，旅游成为首个落地场景，coding 成为第二场景 | **采纳** |

### 方案 C 核心

代码层面旅游该做还做；在**架构抽象**和**简历叙事**上，把 TourSwarm 重新定位成：

> 一个可扩展的个人 Agent 框架。具备 MCP 工具生态 / 多Agent任务编排 / 分层记忆 / Agentic-RAG / 领域验证器五大能力。旅游规划是首个深度落地场景，代码助手是第二场景，验证框架可复用性。

**关键工程动作不是"加旅游功能"，而是"把已有实现抽象出框架层"，并补一个 coding Skill 作为可复用性的硬证据。**

---

## 3. 整体架构

```text
AgentRuntime (通用，所有 Skill 共享)
│  · 上下文管理（压缩/滑窗/持久化）
│  · 分层记忆（Redis 短期 + Mem0 长期 + 三层隔离）
│  · MCP 工具注册与调度
│  · 多Agent任务编排引擎
│  · 外部 Agent 接入（Dify/Coze 适配器，作为工具源）
│  · 流式输出（WebSocket + 工具状态）
│  · RAG 基础设施（VectorStore + Indexer + retrieve 工具）
│
├─ Skill: travel-planning  ← 旅游首个落地场景
│   ├─ tools: amap / weather / scenic / dify-dianping MCP
│   ├─ prompt: 学生穷游助手人设
│   ├─ sub-agents: info → recommend → planning → budget (LangGraph)
│   ├─ verifier: 时间/预算/空间/约束 4 重检查
│   └─ knowledge: 景点库（RAG 检索）
│
└─ Skill: code-assistant  ← 第二场景，对标 Claude Code/Codex
    ├─ tools: file-read / shell / grep / edit MCP
    ├─ prompt: 代码助手人设（agent loop）
    ├─ sub-agents: None（线性迭代，单 ReAct 循环）
    ├─ verifier: None（测试通过内化在 agent loop）
    └─ knowledge: 代码库（可选，后置）
```

### 设计原则

- **能力共享下沉，领域差异上浮**：与场景无关的能力下沉为 Runtime 核心，领域特化内容上浮为 Skill 字段。
- **Skill 是完整助手人格**：一个 Skill = prompt + 工具集 + 子Agent图 + 验证器 + 记忆配置 + 知识源配置。
- **框架根据任务复杂度自适应**：旅游复杂多约束 → 多Agent编排 + 外置验证器；coding 线性迭代 → 单 ReAct 循环 + 内化验证。这种对比本身就是框架可复用性的硬证据。

---

## 4. AgentRuntime 核心抽象

### 4.1 Skill 数据结构

```python
# core/skill.py （新增）
class Skill(BaseModel):
    """一个可插拔的能力单元。一个 Skill = 一个完整的"助手人格"。"""
    name: str                          # "travel-planning" / "code-assistant"
    system_prompt: str                 # 该 skill 的人设和行为约束
    tools: list[ToolSpec]              # 该 skill 可用的 MCP 工具集
    sub_agent_graph: Any | None        # 复杂任务时的多Agent编排（旅游有，coding 无）
    verifier: Verifier | None          # 领域约束验证器（旅游有，coding 无）
    memory_config: MemoryConfig        # 该 skill 的记忆策略
    knowledge_sources: list[KnowledgeSource]  # RAG 知识源配置
```

### 4.2 AgentRuntime 运行流程

```text
用户消息进来
    │
    ▼
AgentRuntime.run(session_id, message)
    │
    ├─ 1. 加载 session 绑定的 Skill
    │     travel-planning → 加载旅游 prompt + amap/weather/scenic 工具
    │     code-assistant  → 加载 coding prompt + file/shell/grep 工具
    │
    ├─ 2. 从分层记忆取上下文（按三层隔离策略）
    │     Redis 取近期对话 + Mem0 取长期偏好
    │
    ├─ 3. ReAct 循环（现有 react_agent.py 核心，改成从 Skill 读 prompt/tools）
    │     LLM 决策 → 调工具 → 观察结果 → 再决策...
    │     └─ 如果 LLM 选中 sub_agent_graph 工具（generate_itinerary）
    │        → 启动 LangGraph 多Agent协作（旅游）/ 跳过（coding 简单任务）
    │
    ├─ 4. 如果 Skill 带 verifier，输出前过验证器
    │     旅游：4 重检查，不过则回炉重规划
    │     coding：（可选）跑测试 / 语法检查
    │
    ├─ 5. 写回分层记忆 + 流式输出
    │
    └─ 返回
```

### 4.3 对现有代码的影响

| 现有文件 | 改动 | 说明 |
|---|---|---|
| `agents/react_agent.py` | 小改 | 硬编码 system_prompt 和 tool 列表改成从 Skill 读 |
| `core/memory/*` | 小改 | 加三层隔离标签（session/skill/user） |
| `mcp_servers/*` | 不改 | 旅游 MCP 原样保留 |
| `agents/itinerary_tool.py` | 不改 | 作为 travel-planning Skill 的 sub_agent_graph |
| `core/verifier.py` | 小改 | 抽象成 Verifier 接口，现有验证器是实现之一 |
| `core/skill.py` | 新增 | Skill 数据结构 + 注册表 |
| `api/services/chat_runner.py` | 小改 | 启动时按 session 选 Skill |

**现有代码约 80% 不动。** 核心改动是把 `react_agent.py` 里的硬编码 prompt/tool 改成 Skill 注入。

### 4.4 三层记忆隔离

不同 Skill 的长期记忆隔离，避免"喜欢海鲜"污染 coding 上下文；但用户身份级偏好跨 Skill 共享。

| 层级 | 隔离方式 | 示例 |
|------|---------|------|
| 短期对话记忆 | 按 session 隔离（已有，不动） | 当前对话历史 |
| Skill 级长期记忆 | 按 skill 标签隔离 | "喜欢海鲜"（仅 travel-planning 可见） |
| 用户级长期记忆 | 全局共享 | "是学生""用 Mac"（所有 Skill 可见） |

实现：Mem0 存储时多带一个 `scope` 元数据（`session` / `skill:xxx` / `user`），检索时按 scope 过滤。

---

## 5. coding Skill 设计

对标 Claude Code/Codex 的 agent loop，但只做 chat 形式 + 工具调用，不做 IDE 集成。

### 5.1 工具集：新建 `mcp_servers/code`

```text
mcp_servers/code/  ← 新增，与 amap/weather/scenic 平级
├── server.py
├── client.py
└── tools:
    ├─ read_file(path)           读文件内容
    ├─ write_file(path, content) 写文件（新建/覆盖）
    ├─ edit_file(path, old, new) 精确字符串替换（非行号，对标 Claude Code 的 Edit）
    ├─ list_dir(path)            列目录树
    ├─ grep(pattern, path)       内容搜索（ripgrep 封装）
    └─ shell_exec(command)       执行 shell（带超时 + 工作目录约束 + 黑名单）
```

### 5.2 关键设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 工具实现方式 | 自研 MCP Server（stdio） | 与旅游侧 3 个 MCP Server 同构，证明 MCP 工具生态可扩展 |
| `shell_exec` 安全边界 | 限定工作目录 + 超时 + 黑名单（rm -rf / 等） | 作品集要能讲"做了安全约束" |
| `edit_file` 语义 | 精确字符串替换 | 对标 Claude Code，比行号更鲁棒 |
| 是否做 `git` 工具 | 不做，用 `shell_exec` 跑 git 命令即可 | YAGNI，避免工具爆炸 |

### 5.3 system prompt（精简版）

```text
你是 CodeAssist, 一个代码助手。你能读写文件、搜索代码、执行命令。

工作流程（agent loop）：
1. 收到任务后，先用 read_file / grep / list_dir 了解代码结构
2. 定位要改的地方，用 edit_file / write_file 修改
3. 用 shell_exec 跑测试或编译验证修改是否正确
4. 失败则回到第 2 步，直到通过或确认无法解决

原则：
- 改代码前先读，不要凭猜测改
- 每次修改后用 shell_exec 验证（跑测试/编译/lint）
- 一次只改一件事，工具调用要原子
- 不知道就说不知道，不要编造 API
```

### 5.4 与旅游侧的对比设计（强化叙事）

| 维度 | travel-planning Skill | code-assistant Skill |
|------|----------------------|---------------------|
| 任务结构 | 复杂多约束（时间/预算/空间交织） | 线性迭代（读→改→测） |
| 编排方式 | ReAct + LangGraph 多Agent图 | 单 ReAct 循环 |
| 验证方式 | 外置确定性验证器（4 重检查） | 内化在 agent loop（跑测试） |
| 亮点 | 多Agent协作 + 验证器消融数据 | agent loop 工程实现 + 安全边界 |

这两个场景的对比证明：**框架能根据任务复杂度自适应——简单任务单循环，复杂任务多Agent编排。** 这是 Claude Code 那种纯 coding 助手讲不出的故事。

---

## 6. 外部 Agent 接入（Dify/Coze）

### 6.1 定位：工具源，不是对等编排者

Dify/Coze 不作为"另一个编排平台"对接，而是**作为工具的一种来源**，被适配成 MCP 注册表里的一个工具。对 AgentRuntime 来说和 amap MCP 没有区别。

| 如果把 Dify/Coze 当成"另一个编排平台" | 把 Dify/Coze 当成"工具源" |
|---|---|
| 要做平台间协议转换、状态同步 | 只包一层 HTTP，当工具调 |
| 架构复杂，叙事讲不清 | 架构统一，所有能力都是工具 |
| 跟框架自身编排能力竞争 | 框架编排是主，外部 agent 是被编排的工具体 |

### 6.2 适配器结构

```python
# core/external_agent.py （新增）
class ExternalAgentAdapter:
    """把外部 Agent 平台（Dify/Coze）包装成 MCP 工具。"""
    name: str                    # "dify-restaurant-recommender"
    description: str             # 给 LLM 看的工具说明
    platform: Literal["dify", "coze"]
    api_key: str
    endpoint: str

    async def call(self, input: str) -> str:
        """调 Dify/Coze 的 HTTP API，返回它们的回复文本。"""
        # Dify: POST {endpoint}/chat-messages
        # Coze: POST {endpoint}/chat
```

对外暴露给 LLM 的就是一个普通工具：`{"action": "dify-restaurant-recommender", "input": "杭州西湖附近人均50的餐厅"}`。

### 6.3 大众点评知识接入

大众点评没有官方开放 API 给个人开发者，但 Dify 上有大众点评的 agent/插件。真实链路：

```text
用户: "杭州西湖附近人均50评分高的餐厅"
  → AgentRuntime (travel-planning Skill)
  → LLM 决策调工具
  → 调 dify-dianping adapter（请求转给 Dify 上的大众点评 agent）
  → Dify agent 返回餐厅列表
  → AgentRuntime 拿到结果，可能再调 amap MCP 查路线
  → 综合回复用户
```

### 6.4 优先级

| 组件 | 优先级 | 理由 |
|------|--------|------|
| `ExternalAgentAdapter` 抽象 + DifyAdapter | P1 | 接大众点评真实场景，证明框架可扩展 |
| CozeAdapter | P2 | 跟 Dify 同构，复制改 endpoint |
| 外部 agent 返回结果喂给后续工具链 | P1 | 体现"编排"，否则只是代理转发 |

---

## 7. 框架级 RAG（Agentic-RAG）

### 7.1 RAG 与记忆的区别

| | 记忆（Memory） | RAG（检索增强） |
|---|---|---|
| 存什么 | 对话产生的信息 | 外部已有知识 |
| 示例 | 偏好/事实/历史 | 景点库/代码库 |
| 写入 | agent 对话中提取 | 预先索引（离线） |
| 读取 | 每轮对话自动注入 | agent 决定要查才查 |
| 目的 | 记住"用户是谁" | 知道"世界有什么" |

记忆每轮自动注入，RAG 是 agent 主动调用工具才触发。两者不能混。

### 7.2 Agentic-RAG：框架天然支持

Agentic-RAG 的本质是把"检索"做成一个工具，让 agent 在 ReAct 循环里自主决定要不要检索、检索什么、结果够不够、要不要再查一次。AgentRuntime 本来就是 ReAct + 工具调用，无需额外编排代码。

对比：

```text
普通 RAG（流水线，死板）:
  用户问题 → [固定检索] → [固定重排] → [生成] → 输出
  问题：检索不到就完了，不会自己补查

Agentic-RAG（本框架天然支持）:
  用户问题 → Agent 思考"要不要查知识库"
           → 调 retrieve 工具 → 看结果
           → "不够，换个关键词再查" → 再调 retrieve
           → "够了" → 生成回答
  优势：agent 自主决策，能多轮检索、能判断结果质量
```

### 7.3 三块组件

```text
AgentRuntime
└─ RAG 基础设施
     ├─ 1. VectorStore 抽象       ← 已有 Qdrant，包一层接口
     ├─ 2. Indexer (离线索引)      ← 新增，把知识源灌进向量库
     └─ 3. retrieve 工具           ← 新增，注册成 MCP 工具，agent 自主调
```

| 组件 | 职责 | 何时跑 |
|------|------|--------|
| `VectorStore` | 向量库抽象（Qdrant 实现），提供 `add`/`search` 接口 | 运行时被调用 |
| `Indexer` | 知识源切片 → embedding → 写入向量库 | 离线脚本 |
| `retrieve` 工具 | 接收 query，调 VectorStore 检索，返回 top-k 文档给 agent | agent 在 ReAct 里自主调 |

### 7.4 每个 Skill 的知识源配置

```python
# travel-planning Skill 的知识源配置
knowledge_sources = [
    {
        "name": "scenic_spots",          # Qdrant collection 名
        "description": "景点数据库",      # 给 LLM 看，告诉它这个知识源装了什么
        "indexer": "scripts/index_scenic.py",  # 离线索引脚本
    }
]

# code-assistant Skill 的知识源配置（可选，后置）
knowledge_sources = [
    {"name": "codebase", "description": "当前项目代码库", ...}
]
```

agent 调 retrieve 时，LLM 根据 Skill 暴露的 `description` 知道有哪些知识源可查。

### 7.5 与现有 `search_scenic_spots` 的关系

现有的 `search_scenic_spots`（景点 MCP Server 的工具）本质是 travel-planning Skill 的一个特化 retrieve。方案 C 后**封装**到框架的 retrieve 机制里（保留原工具实现，外层套统一的 retrieve 接口 + 知识源配置）。这不是重写或删除，是把已有的检索能力抽象成框架通用机制，原工具行为不变。

### 7.6 范围决策

**只做框架级 RAG，不做第三个 Skill（Obsidian 知识库助手）。** 理由：YAGNI。框架级 RAG + 旅游/coding 两个场景的亮点已经足够；Obsidian Skill 留作未来扩展，不在本轮实施。

---

## 8. 落地路线图

```text
Phase 6（方案 C 的全部工作）
│
├─ 6.1 框架抽象层        ← 把现有代码切成 Runtime + Skill
│   ├─ 抽出 core/skill.py (Skill 数据结构 + 注册表)
│   ├─ react_agent.py 改成从 Skill 读 prompt/tools
│   ├─ verifier.py 抽象成 Verifier 接口
│   ├─ 记忆加三层隔离 (session/skill/user 标签)
│   └─ 验收: 旅游侧行为完全不变，测试全绿
│
├─ 6.2 coding Skill      ← 顶替 Pico 的核心交付
│   ├─ 新建 mcp_servers/code (read/write/edit/list/grep/shell)
│   ├─ 写 code-assistant prompt (agent loop)
│   ├─ 前端加 Skill 切换入口
│   └─ 验收: 能读项目文件、改代码、跑测试，agent loop 跑通
│
├─ 6.3 框架级 RAG        ← Agentic-RAG 亮点
│   ├─ VectorStore 抽象 (包 Qdrant)
│   ├─ Indexer 脚本 (景点库先行)
│   ├─ retrieve 工具注册成 MCP 工具
│   ├─ search_scenic_spots 统一到 retrieve 机制
│   └─ 验收: agent 自主决定检索，多轮检索场景跑通
│
├─ 6.4 外部 Agent 接入   ← Dify 接大众点评
│   ├─ core/external_agent.py (Adapter 抽象)
│   ├─ DifyAdapter 实现
│   ├─ 注册成 travel-planning 的工具
│   └─ 验收: "杭州餐厅推荐" 走 Dify 大众点评 agent 返回结果
│
└─ 6.5 简历叙事整理      ← 不是代码，是讲故事
    ├─ README 重写为"个人 Agent 框架"
    ├─ 两个 Skill 对比表 (旅游复杂编排 vs coding 线性迭代)
    ├─ 验证器消融数据 (78% → 94%)
    └─ Agentic-RAG 多轮检索 demo
```

### 依赖关系

```text
6.1 框架抽象 ──→ 6.2 coding Skill
           │
           ├──→ 6.3 框架级 RAG ──→ 6.4 外部 Agent 接入
           │
           └──→ 6.5 叙事整理 (贯穿，边做边记数据)
```

- 6.1 是地基，必须先做
- 6.2 和 6.3 可以并行，建议先 6.2（顶替 Pico 的核心价值先拿到）
- 6.4 依赖 6.3
- 6.5 贯穿全程，每完成一块记数据、写对比

---

## 9. 简历叙事

### 一句话版

> 自研个人 Agent 框架（参照 Claude Code/Codex 架构思想），具备 **MCP 工具生态 / 多Agent任务编排 / 分层记忆（三层隔离）/ Agentic-RAG / 领域验证器** 五大能力。两个落地场景验证框架可复用性：**旅游规划**（多约束任务编排 + 确定性验证器，准确率 78%→94%）+ **代码助手**（agent loop + 文件/shell/grep 工具链）。外部 agent 平台（Dify）作为工具源接入，整合大众点评知识。

### 比 Pico 强在哪

| 维度 | Pico（被替换） | TourSwarm（方案 C 后） |
|------|---------------|----------------------|
| 场景数 | 1（coding） | 2（旅游 + coding），互相印证可复用性 |
| 多Agent编排 | 无或简单 | LangGraph 4-Agent 图 + ReAct 主 Agent |
| 验证器 | 无 | 确定性 4 重验证 + 消融数据（78%→94%） |
| 记忆 | 单层 | 三层隔离（session/skill/user） |
| 工具生态 | 单一 | 4 个自研 MCP Server + 外部 agent 适配器 |
| RAG | 无或普通流水线 | Agentic-RAG（agent 自主多轮检索） |

---

## 10. 非目标（明确不做）

- 不做 IDE 插件 / CLI 集成（那是另一个项目）
- 不做 Obsidian 知识库 Skill（YAGNI，留作未来扩展）
- 不做 Coze 适配器的完整实现（P2，做完 Dify 后复制）
- 不做 coding Skill 的 sub-agent 和 verifier（对比设计，强化叙事）
- 不重写旅游侧已有代码（80% 不动，只做抽象层注入）
- 不在 Dify 上拖拽搭 RAG 工作流（RAG 必须自己实现，否则亮点归 Dify）

---

## 11. 风险与应对

| 风险 | 应对 |
|------|------|
| 框架抽象改动破坏旅游侧行为 | 6.1 完成后旅游侧全量回归测试必须全绿，行为完全不变 |
| coding Skill 工作量超预期 | 6 个工具优先级：read/grep/list 先做（只读），edit/write/shell 后做（写操作 + 安全约束） |
| Dify 大众点评 agent 不稳定 | 适配器层做降级，失败时回退到 amap MCP 的 search_nearby |
| RAG 检索质量差影响 agent 决策 | Agentic-RAG 天然有"多轮检索"容错，agent 会自己换关键词重查 |
| 叙事整理太晚导致数据丢失 | 6.5 贯穿全程，每个子阶段完成立即记数据 |

---

## 附录：决策记录

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-07-05 | 选择方案 C（重定位 + 补抽象层）而非 A/B | 代码已是框架形状，只需正名 + 补抽象；旅游差异化亮点不丢 |
| 2026-07-05 | coding Skill 范围 = chat + 6 工具 | 对标 Claude Code agent loop，不做 IDE 集成，工作量可控 |
| 2026-07-05 | coding Skill 不做 sub-agent 和 verifier | 对比设计强化叙事：框架按任务复杂度自适应 |
| 2026-07-05 | 记忆三层隔离（session/skill/user） | 防跨 Skill 污染，用户级偏好共享，叙事更干净 |
| 2026-07-05 | Dify/Coze = 工具源，不是对等编排者 | 架构统一，框架编排为主 |
| 2026-07-05 | RAG 自己实现，不外包给 Dify | RAG 是亮点，外包则功劳归 Dify |
| 2026-07-05 | 只做框架级 RAG，不做 Obsidian Skill | YAGNI，两个场景亮点已足够 |
