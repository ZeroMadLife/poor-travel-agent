# Knowledge 页面 PRD

## 1. 页面目标

把用户自己的 Obsidian vault、GitHub 仓库或 Markdown 来源整理成可观察、可追溯的 LLM Wiki 图谱。Knowledge 的任务是帮助用户看懂数据库结构和发现值得深入研究的节点，而不是在页面内完成学习对话。

## 2. 用户与任务

### 主要用户

- 已有 Obsidian/GitHub/Markdown 资料的开发者；
- 想知道资料之间如何关联、哪些地方孤立或缺证据的学习者；
- 通过节点选择把问题交给主对话的 Sage 用户。

### 高频任务

1. 导入一个来源并确认读取范围；
2. 观察全局社区、桥接节点和孤立节点；
3. 搜索页面或节点，定位一个概念；
4. hover 查看邻域，click 固定 Inspector；
5. 查看来源页面和 revision；
6. 对缺口节点发起 Deep Research，回到主对话。

## 3. 范围与非目标

### 包含

- K2 沉浸式 Graph Canvas；
- Obsidian 风格自然分布、细边、邻域聚焦和选中高亮；
- 来源导入流程与真实 job 状态；
- Wiki/页面/来源之间的可追溯关系；
- 社区、目标、局部邻域和缺口筛选；
- Inspector、节点列表降级和 Deep Research 交接。

### 不包含

- 常驻 Chat Dock 或完整对话流；
- Knowledge 页面内的独立 chat store/runtime；
- 点击节点立即启动模型调用；
- 前端根据节点度数擅自宣称“知识缺口”；
- 一次性把 5k 节点全部渲染成可读标签；
- 擅自将普通 tag 升级为学习目标。

## 4. 页面结构

```text
Global Navigation
Knowledge Header
  ├─ workspace name / graph revision
  ├─ search
  └─ import source
Source Rail
  ├─ source list
  ├─ import status
  └─ compact filters
Graph Canvas
  ├─ community legend (popover)
  ├─ graph controls
  └─ hover/selected rendering
Inspector (conditional)
  ├─ node/page/revision facts
  └─ view page / deep research
```

## 5. 空态与导入

### 5.1 空知识库

画布空态只解释一句“导入来源后，Sage 会生成可追溯的 Wiki 与关系图谱”，并提供三个入口：

- 导入 Obsidian；
- 连接 GitHub；
- 选择 Markdown 文件/目录。

不显示 85 个统计、社区标签或假的示例图。

### 5.2 导入流程

1. 选择来源类型；
2. 输入路径、仓库或授权信息；
3. 预览文件数量、忽略规则和可能敏感路径；
4. 用户确认；
5. 展示真实 ingest job 阶段：扫描、解析、生成 Wiki、建图、完成/失败；
6. 完成后显示 graph revision 和新增/更新/跳过计数；
7. 失败项可单独重试，不清除已成功的 snapshot。

进度必须来自后端 job/timeline。没有阶段事件时显示“处理中”，不使用自行递增的百分比。

## 6. 图谱交互规格

### 6.1 全局态

- 社区色节点自然散开；
- 边细、低透明但始终存在；
- 只显示少量高权重标签；
- 用户可缩放、拖拽、框选（若实现可支持）；
- 顶部只保留全局/目标/局部、深度、搜索和筛选。

### 6.2 悬停态

- 当前节点放大约 8%；
- 直接邻居和关联边增强；
- 无关节点和边渐隐到可辨识的低透明度，不直接删除；
- tooltip 显示标题、类型、连接数和一条来源摘要；
- 移出后恢复全局，不改变 selected。

### 6.3 选中态

- 节点保留社区色填充；
- 外层使用白色分隔环 + 品牌/蓝色焦点环，渲染层高于节点；
- 直接邻居正常亮度，二跳节点弱化；
- 直接边使用蓝色或 Sage 绿，非相关边渐隐；
- Inspector 固定直到用户关闭、选择另一个节点或按 Escape；
- Inspector 不因鼠标移入详情而丢失 selected。

### 6.4 节点类型

| 类型 | 默认视觉 | 说明 |
| --- | --- | --- |
| page | 社区色圆点 | 可打开 Wiki 页面 |
| source | 稍大圆点/来源标记 | 原始导入对象 |
| goal | Sage 绿色描边 | 与当前目标相关的知识单元 |
| gap | 琥珀描边/虚线环 | 仅后端明确标记的研究缺口 |
| isolated | 低饱和但不隐藏 | 无有效连接，提供研究或归档入口 |

## 7. Inspector

Inspector 是节点详情，不是聊天窗口。至少包含：

- 标题和节点类型；
- 社区和连接数；
- 页面/来源标识；
- `revision`、`graph_revision` 和更新时间；
- 最近证据/引用摘要；
- “查看页面”；
- “在主对话深入研究”；
- 若是 gap/isolated，显示后端给出的原因和建议动作。

### 7.1 Deep Research 交接

点击动作只生成主对话的待提交上下文：

```json
{
  "graph_node": "node_id",
  "page": "page_id",
  "revision": 12,
  "graph_revision": "graph_rev_42"
}
```

用户提交下一轮消息时才冻结；Knowledge 页面只负责提供 selection ref，不负责推理、检索或持久化。

## 8. 性能与降级

| 规模 | 交互 | 视觉策略 | 降级 |
| --- | --- | --- | --- |
| 200 | 全量拖拽、缩放、hover、click | 全边，有限标签 | 无 |
| 1k | 可交互，优先当前邻域 | 标签/边按权重裁剪 | 搜索/列表入口常驻 |
| 5k | 社区入口和局部邻域 | 预计算位置，社区聚合 | 进入局部图后才展开 |
| 超预算 | 搜索、列表、来源浏览 | 不强行 WebGL 全量 | 明确“已切换列表模式” |

当前技术栈约束：继续使用 `sigma`、`graphology`、`graphology-layout-forceatlas2`。任何换库提议必须提供同等交互和性能证据。

## 9. 契约依赖

- graph snapshot：nodes、edges、communities、graph_revision；
- node kind：page/source/goal/gap/isolated 或后端明确枚举；
- page/revision/source refs；
- ingest job：stage、status、counts、error、retry；
- gap reason 与 Deep Research eligibility；
- context receipt freeze confirmation；
- local graph list fallback 的分页/搜索接口。

如果 gap、community 或 snapshot revision 不稳定，UI 只显示可确认字段并隐藏推断性标签。

## 10. 响应式

### 1440/1728

- 来源栏可收起；图谱为主视觉；Inspector 浮层不缩窄画布；
- 控制集中在右下和顶部，不形成左侧多级侧栏。

### 390

- 图谱全屏，顶部仅保留搜索、导入和菜单；
- 来源、筛选、Inspector 使用 bottom sheet；
- 选中详情不得遮挡节点中心和主要关系；
- 同时提供“以列表查看”按钮作为可访问和性能降级入口。

## 11. 验收标准

- 用户不看长说明也能在 10 秒内发现导入入口；
- 全局态能看到细边和自然社区，不能是无边的彩色散点；
- hover 后直接邻域更清晰，无关部分淡出；
- click 后 selected 不被白层覆盖，Inspector 与节点稳定联动；
- 选择 gap/isolated 节点能看到明确的 Deep Research 出口；
- Deep Research 后主对话 composer 显示待提交 frozen context，Knowledge 不创建第二聊天流；
- 200/1k/5k fixtures 按策略可操作，超预算时可搜索、可查看页面；
- 真实导入任务可显示完成/失败/重试，不出现静态假进度；
- 390 下无横向溢出、控制遮挡和不可点击的节点详情。

## 12. 成功指标

- 首次导入确认完成率；
- 导入完成后首次有效节点点击时间；
- hover/selected 后用户查看页面或发起 Deep Research 的比例；
- 孤立/缺口节点被处理的比例；
- 图谱列表降级后的搜索成功率；
- 节点交接到主对话后形成有效提问的比例。
