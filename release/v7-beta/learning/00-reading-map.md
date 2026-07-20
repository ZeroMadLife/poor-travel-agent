# Sage learning 阅读地图

这套笔记不是 Sage 的宣传文档，也不是把每个 Python 文件翻译成中文。它要解决的问题是：**我们虽然通过 Vibe Coding 做出了 Sage，但如何真正看懂它、验证它，并在秋招时能把每个设计决策讲清楚。**

阅读时始终把 Sage 看成一个 **Personal AI Learning Companion harness**：

```text
模型能力
  + 工具执行
  + 上下文管理
  + 权限与审批
  + 持久记忆
  + 知识检索
  + 受限子代理
  + 运行状态
  + 可追溯证据
  + Web 交互
= 一个能连接个人项目、笔记、文档，持续形成知识资产的系统
```

## 这套文档和发布文档的差别

| 文档 | 目的 | 读法 |
| --- | --- | --- |
| `release/v7-beta/CHANGELOG.md` | 发布变更摘要 | 看本版改了什么 |
| `release/v7-beta/REVIEW.md` | 架构评审包 | 拿着做评审 |
| `release/v7-beta/TESTING.md` | 测试入口与场景 | 跑验收 |
| `release/v7-beta/learning/` | **本目录**：深度讲解每个模块为什么存在 | 准备面试追问、做架构分享 |

CHANGELOG 回答"改了什么"，learning 回答"**为什么这么设计**"。

## 源码事实口径

- 项目：`/Users/zeromadlife/Desktop/tour-agent`
- 分支：`dev/sage-v7`
- Harness 包：`packages/sage_harness/`（应用中立，可独立发布）
- 应用适配层：`core/harness/`（21 个 adapter）
- 旧 runtime（legacy）：`core/coding/`（CodingRuntime + XML Engine）
- Knowledge 平台：`core/knowledge/`（Wiki + RAG + citation + revision）
- 前端：`frontend/src/views/CodingView.vue`、`frontend/src/stores/coding*.ts`
- 验证入口：`tests/harness/`、`tests/core/coding/`、`tests/core/knowledge/`、`tests/api/`

文档里的状态标记含义：

| 标记 | 含义 |
| --- | --- |
| **已实现** | 当前源码和测试里都能找到对应行为 |
| **部分实现** | 主路径存在，但能力、交互或正确性尚未完整 |
| **规划中** | 只出现在设计书或 V8 路线里 |
| **复盘风险** | 源码存在，但仍应重点审查或补强 |

设计书描述"应该是什么"，源码描述"现在是什么"。二者冲突时，本手册以源码和测试为事实，并把差异写进"当前边界"。

## 推荐阅读顺序

### 第一遍：建立全局地图（面试第一轮常问）

1. [[01-why-sage]] - 为什么做 Sage，和 ChatGPT/Claude Code 差在哪
2. [[02-overall-architecture]] - 三层架构与请求主链路
3. [[03-runtime-engine]] - Runtime 与 Engine 的职责拆分

这一遍不要追逐每个函数，只回答三个问题：**请求从哪里进来、谁推进任务、证据最终存在哪里。**

### 第二遍：理解 Harness 为什么可靠（面试第二轮深挖）

4. [[04-context-prompt-caching]] - Prompt 怎么拼，cache 怎么命中
5. [[05-tools-registry]] - 工具怎么注册、怎么发现、怎么限制
6. [[06-permissions-approval-sandbox]] - 五道门与沙盒
7. [[07-skills-commands]] - Skills 与 slash 命令
8. [[08-memory-dream]] - 长短记忆与 Dream 反思

这一遍重点看边界：**模型不能直接写文件，工具不能绕过权限，Memory 不能无来源地注入，Dream 不能自动写入长期记忆。**

### 第三遍：理解知识平台与多 Agent（差异化亮点）

9. [[09-knowledge-platform]] - Knowledge Platform：Wiki + RAG + 引用
10. [[10-subagents-research]] - 受限子代理：Research/Synthesize/Practice
11. [[11-timeline-reconnect]] - 持久 Timeline 与断线重连

这一遍要能讲清楚：**为什么 Sage 不只是"另一个 ChatGPT"，差异化在哪。**

### 第四遍：安全与收尾

12. [[12-security-audit]] - 安全审计与防注入
13. [[13-module-map]] - 模块速查表

这一遍重点看：**哪些地方必须 fail-closed，哪些攻击面已经被覆盖，哪些还没有。**

## 一张图记住主线

```text
Vue Assistant Shell / Coding Workbench
  -> Pinia useCodingStore
  -> CodingStream(WebSocket)
  -> api/coding.py::coding_stream
  -> CodingRuntime.run_turn (legacy)
     或 HarnessRuntimeAdapter.run_turn (deerflow_v2)
  -> Engine.run_turn / create_agent
  -> ToolExecutor.execute / Middleware 链
  -> RegisteredTool.execute
  -> typed RunEvent
  -> SessionEventJournal (SQLite) + RunStore trace + WebSocket
  -> applyCodingEvent reducer
  -> 聊天、审批、Diff、Run History、引用更新
```

## 读源码的方法

每章都按同一个动作读：

1. 先打开章节列出的"第一入口"。
2. 只跟一条调用链，不同时展开所有 import。
3. 找到状态落点：内存对象、session JSON、trace JSONL、timeline SQLite 或 diff artifact。
4. 打开对应测试，观察测试怎样构造输入、怎样断言事件。
5. 用自己的话回答章末自测题。

## 不要混淆的几套系统

| 系统 | 回答的问题 | 当前阶段 |
| --- | --- | --- |
| Durable Memory | 用户明确要求 Sage 长期记住什么 | V7 已实现 SQLite revisioned |
| Knowledge RAG | 当前问题应该检索哪些知识片段 | V7 已实现 PostgreSQL + pgvector + RRF |
| Context Summary | 当前任务怎么接着干 | V7 已实现结构化 compaction |
| AST 知识图谱 | 类、函数、文件之间如何结构化连接 | V8 规划 |
| Learning State | 用户对某个知识点掌握到什么程度 | V7 Practice profile 候选实现 |

Memory 不是 RAG，RAG 也不是知识图谱，Context Summary 不是 Memory。它们生命周期、信任等级、写入语义都不同，不能因为"听起来像记忆"就塞进同一个模块。

## 相关资料

- 设计书：`docs/superpowers/specs/`
- Obsidian 学习库：`Obsidian-Knowledge-Base/03_项目/tourswarm/技术沉淀/sage-learning/`（40+ 篇复盘）
- 竞品参考：Claude Code / Hermes Agent / OpenClaw / Hermes Studio / DeerFlow 2.x / Pico v3
