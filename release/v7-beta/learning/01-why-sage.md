# 01 - 为什么做 Sage

> 本章目标：能回答"Sage 是什么、为什么不是另一个 ChatGPT、为什么不在 Coding 工具赛道和 Codex/Claude Code 硬碰硬"。

## Sage 到底解决什么问题

Sage 的起点是一个朴素观察：**程序员的学习和成长缺一个"懂你"的系统。**

一个程序员在学习新技术、维护老项目、准备面试时，手上的资料是分散的：

- 电脑里的代码仓库（GitHub clone、公司项目、个人实验）
- Obsidian/Notion 里的笔记（踩坑记录、设计思路、面试题）
- 浏览器收藏夹里的文章、论文、视频链接
- 飞书/微信里和同事讨论的片段
- 自己写过但已经忘记的代码

这些资料之间是有联系的：一段笔记解释了某个仓库里的设计，一篇论文是某个面试题的答案，一段代码验证了某个概念。但**没有任何系统把这些资料连起来**。

ChatGPT/Claude 能回答通用问题，但它们**不知道你的项目、不知道你的笔记、不知道你上次踩过什么坑**。每次对话都从零开始。

Sage 要解决的就是这个：**连接个人项目、笔记、文档和外部资料，通过检索、对话、实践、验证、复盘与人工批准，持续形成个人知识资产。**

## 为什么不做"另一个 ChatGPT"

市面上已经有 ChatGPT、Claude、Gemini、通义、Kimi、DeepSeek。再做一个通用聊天框没有差异化。Sage 的差异化在于：

**Sage 知道你的材料，回答基于你自己的资料，带可验证引用。**

举个例子：
- 问 ChatGPT："React Fiber 架构解决了什么问题？" -> 回答基于训练数据，可能过时，无引用
- 问 Sage（已导入 `facebook/react` 仓库）："React Fiber 架构解决了什么问题？" -> 回答基于仓库里的源码 + 你的笔记，每段附 `[来源: packages/react-reconciler/src/ReactFiber.js:45]`，点击跳转

这个差异化的本质是：**Sage 的回答是可验证的，不是模型瞎编的。** 引用必须指向真实的知识源 revision，模型不能凭空生成引用。

## 为什么不做"另一个 Claude Code"

Codex、Claude Code、Cursor、Continue 已经覆盖通用编码。它们有更强的模型、更成熟的工具、更完整的生态。Sage 在"更多工具 / 更像 Claude Code 的 UI"上竞争是高投入低差异化。

Sage 的判断是：**通用编码工具的赛道已经卷死了，但"连接个人材料的 AI 学习伴侣"还是空白。**

所以 Sage 保留 Coding Runtime，但把它降级为 **Practice Engine**：

```
Sage = 个人助手主壳
  ├── Knowledge Platform（连接材料 + RAG + 引用 + Wiki）
  ├── Coding Runtime（Practice Engine：源码阅读、代码实验、测试验证）
  ├── Memory（用户确认的长期事实）
  ├── Dream（反思 proposal，不自动写入）
  └── 受限子代理（Research/Synthesize/Practice）
```

Coding Runtime 不再是首页唯一叙事。首页是 `/assistant`，不是 `/coding`。

## Sage 的核心闭环

```text
知识摄取（导入仓库/笔记/网页/PDF）
  ↓
知识建模（概念/技能/依赖/来源/掌握度）
  ↓
目标 + 诊断（用户想学什么，当前掌握到什么程度）
  ↓
学习计划（分阶段，可调整）
  ↓
实践 + 验证（coding/Q&A/test/Feynman 解释/真实产物）
  ↓
复盘 + 沉淀（错误归因、能力证据、Memory Proposal、下一步调整）
  ↓
（循环）
```

这个闭环里有几个关键设计约束：

1. **Learning State 更新必须绑定可验证证据**。不能靠模型说"用户应该懂了"就更新掌握度。掌握度来自能力权重和验证证据（Practice profile 产生的 Mastery Evidence 候选）。
2. **Dream 只能生成 proposal**。不能自动修改长期记忆或已验证 Wiki。涉及长期事实、Knowledge/Wiki 或敏感偏好时必须用户确认。
3. **知识写入必须走 proposal**。模型不能直接持久化到 KnowledgeStore，避免幻觉污染知识库。

## 和竞品的对标

| 维度 | Sage v7-beta | ChatGPT | Claude Code | Hermes Studio |
| --- | --- | --- | --- | --- |
| 主产品 | 个人 AI 学习伴侣 | 通用聊天 | 通用编码 | 多渠道 Agent 控制台 |
| 知识源连接 | GitHub 仓库 + Obsidian + 网页 + PDF | 无 | 当前 workspace | 文件系统 |
| 引用可验证 | ✅ Knowledge revision + content hash | ❌ | ❌ | 部分 |
| 长期记忆 | ✅ SQLite revisioned + proposal | ❌ | CLAUDE.md | ✅ Mem0 |
| 梦境反思 | ✅ Dream proposal-only | ❌ | ❌ | ✅ background review |
| 受限子代理 | ✅ Research/Synthesize/Practice | ❌ | ✅ Task tool | ✅ delegate |
| 持久 timeline | ✅ SQLite + 重连重放 | ❌ | ❌ | ✅ session DB |
| 部署形态 | Web + Docker Compose | 云端 SaaS | 本地 CLI | Web + Electron |
| 开源 | ✅ MIT | ❌ | ❌ | BSL 1.1 |

Sage 的优势不在单一功能，而在**把这些能力组合成一个学习闭环**：连接材料 -> 检索 -> 对话 -> 实践 -> 验证 -> 沉淀 -> 复盘。

## 为什么选 Web 形态

Pico 是本地 CLI/TUI，Claude Code 是本地 CLI，Cursor 是 Electron 桌面应用。Sage 选 Web 是因为：

1. **群友试用零门槛**。发个链接就能用，不用安装。
2. **多用户隔离天然**。每个用户一个 workspace，互不可见。
3. **移动端可用**。手机浏览器直接访问，不用做 App。
4. **服务器端 RAG**。embedding 和检索在服务器跑，不占用用户本地资源。

代价是：
- 浏览器不能直接读用户电脑上的任意目录（需要 V8 Local Companion）
- 需要服务器运维（部署、备份、监控）
- 延迟比本地 CLI 高（网络往返）

## 现在的判断

Sage v7-beta 已经形成一个可评审的 harness：

- `packages/sage_harness/` 是应用中立的 Harness 包（可独立发布）
- `core/harness/` 是 21 个 adapter，把 Sage 业务事实接到 Harness Port
- `core/coding/` 是 legacy runtime（XML Engine，历史兼容）
- `core/knowledge/` 是 Knowledge Platform（Wiki + RAG + citation）
- `frontend/src/` 是 Vue 工作台（Assistant 首页 + Coding 工作台 + Knowledge 视图）

它不是 Codex/Claude Code 的替代品，也不是 ChatGPT 的克隆。它是一个**面向程序员个人学习和知识沉淀的 AI 伴侣**。

## 第一入口

按顺序打开：

1. `frontend/src/views/AssistantHomeView.vue` - 首页主入口
2. `api/coding.py::coding_stream` - WebSocket 边界
3. `core/coding/runtime.py::CodingRuntime.__init__` - legacy runtime 组装
4. `core/harness/runtime_adapter.py` - v2 runtime 适配
5. `packages/sage_harness/sage_harness/agents/factory.py` - create_agent 工厂

## 测试证据

- `tests/api/test_coding_routes.py` - API 契约
- `tests/harness/test_agent_factory.py` - Harness agent 工厂
- `tests/core/coding/test_runtime_run_lifecycle.py` - run 生命周期

## 当前边界

> [!warning] v7-beta 不是生产就绪
> - 多用户隔离的 Container Sandbox 未在目标服务器真实验证
> - `deerflow_v2` 默认 gate 关闭，默认走 legacy runtime
> - onboarding 引导和知识源导入入口前端不完整
> - 审批的 LangGraph durable interrupt 未实现

## 自测

1. Sage 和 ChatGPT 的核心差异是什么？为什么这个差异能留住用户？
2. 为什么不直接和 Claude Code 在编码工具赛道竞争？
3. Sage 的学习闭环里，为什么 Learning State 不能靠模型自评分更新？
4. 为什么选 Web 形态而不是本地 CLI？

下一章：[[02-overall-architecture]]
