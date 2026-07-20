# 09 - Knowledge Platform

> 本章目标：能讲清 Knowledge Platform 的数据模型（Workspace/Source/Page/Revision/Proposal）、混合检索（PostgreSQL FTS + pgvector + RRF）、引用可验证（citation + revision + content hash）、以及为什么知识写入必须走 proposal。

## Knowledge Platform 是 Sage 的差异化核心

ChatGPT/Claude 能回答通用问题，但它们不知道你的项目和笔记。Sage 的差异化在于：**知道你的材料，回答基于你自己的资料，带可验证引用。**

这个差异化的技术实现就是 Knowledge Platform。没有它，Sage 就是另一个聊天框。

## 数据模型

### 五个核心实体

```text
KnowledgeWorkspace
  ├── purpose.md / schema.md / index.md / log.md
  ├── raw/sources/           # 不可变来源
  ├── pages/                 # LLM Wiki Markdown
  └── proposals/             # Wiki 更新提案

KnowledgeSource              # 知识来源
  ├── source_kind: github_repo | obsidian_vault | web_page | pdf
  ├── canonical_url / content_hash
  └── revision

KnowledgePage                # Wiki 页面
  ├── page_id / title / slug
  └── current_revision

KnowledgePageRevision        # 页面版本
  ├── revision_id / page_id
  ├── content (Markdown)
  ├── citation_refs[]        # 引用哪些 source
  └── evidence_refs[]        # 哪些 evidence 支持这次修改

KnowledgeProposal            # 知识写入提案
  ├── proposal_id
  ├── status: pending | approved | rejected
  ├── base_revision
  └── changes[]
```

### 逻辑目录结构

```
knowledge-workspace/
├── purpose.md          # 这个知识空间为什么存在
├── schema.md           # 页面类型、命名、写入和审核规则
├── index.md            # 页面目录和一行摘要
├── overview.md         # 当前综合概览
├── log.md              # append-only 操作记录
├── raw/
│   └── sources/        # 不可变来源或来源快照
├── pages/              # LLM Wiki 式持久 Markdown
└── proposals/          # 待审阅的 Wiki 更新提案
```

### 借鉴边界

- **Karpathy LLM Wiki pattern**（公开方法）：原始来源/Wiki/Schema 三层，`Ingest / Query / Lint` 三种操作，`index.md`/`log.md`/YAML frontmatter/`[[wikilink]]`
- **nashsu/llm_wiki**（GPLv3）：**只参考产品行为，不复制源码**。Sage 数据契约和代码均独立实现。

## 知识摄取（Ingest）

### 知识源提案

知识源不能被 Agent 直接添加，必须走提案：

```python
@dataclass(frozen=True)
class KnowledgeSourceProposal:
    proposal_id: str
    workspace_id: str
    owner_id: str
    source_kind: str          # github_repo | obsidian_vault | web_page | pdf
    canonical_url: str
    content_hash: str
    status: str               # pending | applying | approved | rejected
    revision: int
    target_root_id: str
    target_relative_path: str
    job_id: str | None
    ...
```

**为什么走提案**：知识源是长期资产。如果模型能直接添加，它可能被 prompt injection 诱导添加恶意 URL。提案让用户显式确认"这个 URL 可以导入"。

### 摄取 Job

```
KnowledgeSourceProposal approved
  ↓
摄取 Job（异步队列 + 租约 + 重试 + 恢复）
  ├── git clone（GitHub 仓库）
  ├── 文件解析（Obsidian/Markdown 文件夹）
  ├── 网页抓取（web_page，走安全 Web Fetch）
  ├── PDF 解析（pdf，异步队列）
  ↓
分块（chunk_document）
  ↓
embedding（DenseEmbeddingProvider）
  ↓
PostgreSQL 全文检索索引 + pgvector 向量索引
  ↓
原始来源归档到 raw/sources/（不可变）
```

`KnowledgeStore` 用 SQLite 存元数据（proposal/page/revision），PostgreSQL 存检索索引（FTS + pgvector）。这两个是不同的事实源：SQLite 是知识资产事实源，PostgreSQL 是检索事实源。

## 混合检索（Hybrid Retrieval）

### 为什么不只用向量检索

纯向量检索的问题：
- 对精确术语（函数名、文件路径、版本号）不敏感
- 中文 embedding 质量参差不齐
- 单一分数难以解释

纯全文检索的问题：
- 语义相似但用词不同的查不到
- 无法理解同义词

Sage 用 **PostgreSQL FTS + pgvector + RRF** 混合：

```python
def retrieve(query: str, workspace_id: str, top_k: int = 5) -> KnowledgeRetrievalBundle:
    # 1. 全文检索（lexial_terms + fts_query）
    fts_hits = postgres_fts_search(query, workspace_id, limit=top_k * 3)

    # 2. 向量检索（embedding + pgvector）
    query_vec = embedding_provider.embed(query)
    vec_hits = postgres_vector_search(query_vec, workspace_id, limit=top_k * 3)

    # 3. RRF 融合
    fused = rrf_merge(fts_hits, vec_hits, k=60)

    # 4. 取 top_k
    return KnowledgeRetrievalBundle(hits=fused[:top_k], ...)
```

### RRF（Reciprocal Rank Fusion）

RRF 是经典的 rank fusion 算法：

```python
def rrf_merge(fts_hits, vec_hits, k=60):
    scores = {}
    for rank, hit in enumerate(fts_hits):
        scores[hit.id] = scores.get(hit.id, 0) + 1 / (k + rank + 1)
    for rank, hit in enumerate(vec_hits):
        scores[hit.id] = scores.get(hit.id, 0) + 1 / (k + rank + 1)
    return sorted(hits, key=lambda h: scores[h.id], reverse=True)
```

**为什么用 RRF**：不需要校准两个检索器的分数尺度（FTS 分数和向量相似度不可比），只看排名。简单且有效。

### 为什么不引入 Elasticsearch/Milvus/Neo4j

V7 首版用 PostgreSQL 内置能力：
- `tsvector` + `tsquery` 做全文检索
- `pgvector` 扩展做向量检索
- 都在同一个数据库，事务一致

引入外部组件的代价：
- 运维复杂度 +1（多一个服务要部署/监控/备份）
- 数据一致性 +1（PostgreSQL 和 Elasticsearch 之间同步）
- 资源占用 +1（Milvus 吃内存）

**判断**：V7 首版 PostgreSQL 够用。等数据量到百万级 chunk 或检索延迟不可接受时再引入。

## 引用可验证（Citation）

### 每段回答带引用

```
Sage 回答：React Fiber 架构解决了 React 15 的同步渲染阻塞问题。
它把渲染拆分成可中断的工作单元，通过 fiber 节点树追踪优先级。

[来源: packages/react-reconciler/src/ReactFiber.js:45]
[来源: packages/react-reconciner/src/ReactFiberBeginWork.js:120]
```

引用不是模型瞎编的，必须指向真实的 Knowledge source revision。

### Citation 的数据结构

```python
@dataclass(frozen=True)
class KnowledgeEvidence:
    chunk_id: str
    page_id: str
    source_id: str
    source_kind: str           # github_repo | obsidian_vault | web_page | pdf
    canonical_url: str
    content_hash: str          # source 内容 hash
    revision: int              # source revision
    excerpt: str               # 命中的文本片段
    score: float
```

**关键**：
- `canonical_url` + `content_hash` + `revision` 三件套。即使 URL 不变，内容变了 hash 也变，旧引用失效。
- `excerpt` 是实际命中的文本片段，用户点击引用能看到这段原文。
- 模型不能凭空生成 citation。citation 必须来自检索结果。

### 引用失效

如果 Knowledge source 被更新（如 GitHub 仓库新 commit），旧 revision 的 citation 仍然有效（指向历史版本），但会标记为"stale"。用户可以看到"这个引用基于旧版本，最新版本可能不同"。

## 知识写入必须走 Proposal

### 为什么不能自动写入

和 Dream 一样，模型会幻觉。如果模型能直接写 Knowledge page，幻觉就会污染知识库。

所以 Knowledge 写入走 proposal：

```
模型调用 knowledge_learn tool
  ↓
生成 KnowledgeProposal（pending）
  ├── changes: [MemoryChange(...)]
  ├── evidence_refs: [KnowledgeEvidence(...)]  # 必须有证据
  └── base_revision: 当前 page revision
  ↓
用户审阅
  ├── approve: 原子写入 page + 生成新 revision
  ├── reject: 不修改
  └── edit: 用户修改 changes 后 approve
```

### knowledge_learn tool

```python
@register_tool(
    name="knowledge_learn",
    description="Propose a knowledge page update based on evidence.",
    schema={"page_id": "str", "changes": "list", "evidence_refs": "list"},
    schema_model=KnowledgeLearnArgs,
    risky=False,
    category="knowledge",
    deferred=True,
)
def knowledge_learn(workspace, args, tool_context):
    # 1. 验证 evidence_refs 都来自真实检索结果
    # 2. 创建 KnowledgeProposal（pending）
    # 3. 不直接写入 page
    return ToolResult(content=f"proposal created: {proposal_id}")
```

**关键**：`knowledge_learn` 只创建 proposal，不写 page。evidence_refs 必须是真实检索结果的 chunk_id。

### Wiki 更新 Proposal

Wiki 页面更新也走 proposal：

```
模型认为某个 page 需要更新
  ↓
生成 KnowledgeProposal
  ├── page_id: 现有 page
  ├── changes: 新 content + 修改原因
  └── evidence_refs: 支持这次修改的证据
  ↓
用户审阅
  ├── approve: 生成新 KnowledgePageRevision
  └── reject: 保持原样
```

每次修改都是新 revision，可以回溯历史。`log.md` 记录所有操作。

## Dream/Reflection 与 Knowledge 的关系

Dream 反思的 evidence 可以来自 Knowledge 检索：

```
Dream Reflection Agent
  ├── 读取 evidence bundle
  │   └── 包含 KnowledgeEvidence（citation + revision）
  ├── 生成 MemoryProposal（写入 Memory）
  └── 或生成 KnowledgeProposal（写入 Knowledge Wiki）
```

两者都是 proposal-only，用户确认后才写入。

**关键区别**：
- MemoryProposal 写入 MemoryStore（稳定事实）
- KnowledgeProposal 写入 KnowledgeStore（结构化 Wiki 页面）

Dream 不能自动写入任何一个。

## knowledge_search tool

```python
@register_tool(
    name="knowledge_search",
    description="Search the connected knowledge sources for relevant information.",
    schema={"query": "str", "top_k": "int=5"},
    schema_model=KnowledgeSearchArgs,
    risky=False,
    category="knowledge",
    deferred=True,
)
def knowledge_search(workspace, args, tool_context):
    # 1. 调用 KnowledgeRetrievalService.retrieve()
    # 2. 返回 KnowledgeRetrievalBundle（含 citation）
    # 3. 模型基于检索结果回答，引用 citation
    return ToolResult(content=json.dumps(bundle.to_dict()))
```

模型在 ReAct 循环中调用 `knowledge_search`，拿到带 citation 的检索结果，基于它回答。这是 Sage 差异化的核心交互。

## 和竞品的对标

| 维度 | Sage v7-beta | ChatGPT | Claude Code | Hermes |
| --- | --- | --- | --- | --- |
| 知识源连接 | GitHub + Obsidian + 网页 + PDF | 无 | 当前 workspace | 文件系统 |
| 检索方式 | PostgreSQL FTS + pgvector + RRF | 无 | 无 | Mem0 vector |
| 引用可验证 | ✅ citation + revision + content_hash | ❌ | ❌ | 部分 |
| 知识写入 | proposal-only + 用户审批 | N/A | CLAUDE.md | auto memory |
| Wiki 产物 | LLM Wiki Markdown + 版本管理 | 无 | 无 | 无 |
| 向量数据库 | pgvector（PostgreSQL 内置） | 无 | 无 | Qdrant |

Sage 的 Knowledge Platform 是 ChatGPT/Claude Code 都没有的。这是 Sage 能在"个人学习伴侣"赛道差异化的核心。

## 第一入口

按顺序打开：

1. `core/knowledge/store.py::KnowledgeStore` - 知识存储（SQLite 元数据）
2. `core/knowledge/retrieval.py::retrieve` - 混合检索 + RRF
3. `core/knowledge/retrieval.py::chunk_document` - 分块
4. `core/knowledge/source_proposals/types.py::KnowledgeSourceProposal` - 知识源提案
5. `core/coding/tools/knowledge_tools.py::knowledge_search` - 检索工具
6. `core/coding/tools/knowledge_tools.py::knowledge_learn` - 学习工具
7. `core/harness/knowledge_adapter.py` - v2 知识适配
8. `core/harness/evidence_bundle.py` - Evidence Bundle

## 测试证据

- `tests/core/knowledge/test_store.py` - 知识存储
- `tests/core/knowledge/test_retrieval.py` - 检索 + RRF
- `tests/core/knowledge/test_source_proposals.py` - 知识源提案
- `tests/api/test_coding_memory_routes.py` - Knowledge API
- `tests/harness/test_knowledge_adapter.py` - v2 适配

## 当前边界

> [!warning] Knowledge Platform 有几个已知边界
> - onboarding 引导未实现（用户不知道怎么连知识源）
> - 知识源导入前端入口不显式（群友试用前必须补）
> - RAG 能用但"生硬"（检索质量取决于 chunk 策略和 embedding 质量）
> - pgvector 需要服务器安装扩展
> - 网页抓取的 safe fetch 偶尔超时
> - PDF 解析异步队列实现但未大规模验证
> - Knowledge Wiki 的 Lint 操作未实现

## 自测

1. Knowledge Platform 解决什么问题？为什么是 Sage 的差异化核心？
2. 五个核心实体（Workspace/Source/Page/Revision/Proposal）各自的作用？
3. 为什么用 PostgreSQL FTS + pgvector + RRF 而不是引入 Elasticsearch/Milvus？
4. Citation 的 `canonical_url + content_hash + revision` 三件套解决什么问题？
5. 知识写入为什么必须走 proposal？如果自动写入会怎样？
6. `knowledge_search` 和 `knowledge_learn` 的区别？
7. Dream 反思和 Knowledge Wiki 的关系？

下一章：[[10-subagents-research]]
