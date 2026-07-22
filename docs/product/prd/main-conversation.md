# 主对话 PRD

## 1. 页面目标

让用户从一个自然目标开始，在同一条可恢复的 Harness 对话里完成检索、研究、练习、审批和知识沉淀。用户不需要先理解 Thread、Run、Timeline 或 RAG 的技术名词。

核心判断：主对话是唯一的行动入口；Knowledge、Coding、Memory 都通过事实、上下文和明确动作回到这里。

## 2. 用户与任务

### 主要用户

- 需要系统学习一个具体领域的开发者；
- 希望将 Obsidian/GitHub 知识转为可检索工作上下文的工程师；
- 需要看到真实执行证据，而不是只看一段漂亮回答的面试官/评审者（通过公开门面，不进入私人页面）。

### 高频任务

1. 描述一个学习/交付目标并确认完成条件；
2. 继续上次没有完成的目标；
3. 让 Sage 检索已有知识，必要时补充 Web/MCP 证据；
4. 发起实践、代码测试或任务执行；
5. 审阅 Wiki/Memory/Plan 增量 proposal；
6. 查看本轮真实状态，失败后恢复或明确放弃。

## 3. 范围

### 包含

- A1 `Dialogue + Facts` 布局；
- Goal header、Goal contract 和下一步；
- 消息、工具摘要、审批、Evidence、Proposal、Recovery；
- 唯一 Chat Harness、唯一 composer、唯一 timeline；
- Knowledge context 待提交/已冻结回执；
- 运行状态未开始、运行、工具、审批、失败、完成、恢复；
- 桌面 1728/1440 与移动 390。

### 不包含

- 新建第二套聊天 runtime/store；
- 在主对话中直接修改后端 Goal/Mastery 契约；
- 自动把模型自评转成 mastery；
- 在没有 proposal/approval 时写入长期 Knowledge 或 Memory；
- 公开门面读取私人 Session。

## 4. 信息结构

```text
Global Navigation
  └─ Thread list / Goal switcher
Conversation
  ├─ Goal header
  ├─ Message timeline
  ├─ Run summary / expandable evidence
  └─ Composer
Facts Rail
  ├─ Pending approval / blocker
  ├─ Current goal
  ├─ Run state
  ├─ Evidence / proposal
  └─ Context & usage summary
```

事实栏不是第二个信息流。它只展示可以改变用户下一步决策的事实。

## 5. 关键状态与文案

| 状态 | 显示 | 主要动作 |
| --- | --- | --- |
| 新用户空态 | 当前 Purpose 摘要 + 3 个任务建议 | 开始目标、导入知识、查看最近工作 |
| Goal 草稿 | 可编辑目标、成功条件、范围和验证方式 | 确认 Goal、继续编辑 |
| 未开始 | “等待你的下一步” | 发送消息、打开 Knowledge |
| 运行中 | 当前真实 stage + elapsed + 可展开事件 | 停止、查看事实 |
| 等待工具 | 工具名、输入摘要、真实开始时间 | 等待、取消（若契约支持） |
| 等待审批 | 风险/影响/变更摘要 | 批准、拒绝、编辑 |
| 失败 | 失败原因、最后稳定 checkpoint | 恢复、重试、结束本轮 |
| 完成 | 一句话结果 + evidence 数量 + next action | 继续目标、审阅沉淀 |

不显示“模型正在思考”作为独立事实；模型输出只能出现在消息或真实 event 摘要中。

## 6. 关键流程

### 6.1 从目标开始

1. 用户输入“我想学/完成……”；
2. Sage 生成可编辑 Goal 草稿：目的、完成条件、证据类型、范围；
3. 用户确认后创建 Thread Goal；
4. 页面进入未开始状态并提示下一步；
5. 每次 run 结束更新真实 evaluation、evidence refs 和 next action。

### 6.2 Knowledge 节点交接

1. 用户在 Knowledge 选中节点；
2. 点击“在主对话深入研究”；
3. 主对话 composer 上方显示 `graph_node / page / revision / graph_revision` 摘要；
4. 用户编辑并提交问题；
5. 提交时冻结 `surface_context`；
6. timeline 记录 context receipt，后续检索只使用已冻结引用。

### 6.3 Proposal 审阅

1. timeline/API 返回待审阅 proposal；
2. Facts Rail 提升为第一优先级；
3. 用户展开查看来源、变化、风险和目标位置；
4. 批准/拒绝使用 `expected_revision`；
5. 409 显示“内容已更新，请重新打开”，不覆盖其他决定；
6. 完成后 Facts Rail 收缩为审计摘要。

### 6.4 失败与恢复

1. 运行进入 failed/interrupted；
2. Facts Rail 显示最后稳定 checkpoint 和已发生副作用；
3. 用户选择恢复、重试或结束；
4. 恢复沿用既有 run/thread/timeline，不重新伪造一条运行；
5. 页面在刷新或断线后仍能从服务端状态重建。

## 7. 数据与契约依赖

### 已有/可复用

- `useHarnessSession`、`useCodingStore` 的单一 session/runtime；
- `timelineProjection.ts`、`runVisualState.ts`；
- `surfaceContext.ts`；
- H2.7B Goal 的 manual/bounded_auto、revision/CAS 和 follow-up 状态；
- H2.8B retrieval memory 相关事件和 usage 投影。

### 待确认

- Goal evaluation 的稳定前端 DTO：status、criteria、evidence refs、next_action、typed blocker；
- Mastery Ledger 的 goal/capability 聚合展示接口；
- frozen receipt 的后端确认字段与重放语义；
- proposal 类型统一的 review bundle；
- composer 发送失败、取消和抢占的明确事件。

缺口只进入 contract-gap 文档，不在页面内猜测。

## 8. 响应式要求

### 1728

- Facts Rail `320px`；目标标题和消息正文保持舒适行宽；
- timeline 细节可在事实栏或 drawer 查看。

### 1440

- Facts Rail `288px`，允许收起；
- 对话正文不少于 `620px`；
- 详细工具输入/输出使用 drawer。

### 390

- 单列消息；Facts 以 bottom sheet 打开；
- composer 固定底部，按钮与输入不被键盘遮挡；
- Goal 标题允许两行，不截断完成条件；
- 核心动作触控面积不小于 `44px`。

## 9. 验收标准

- 首次进入 30 秒内能找到主输入框并理解“目标 -> 下一步”的关系；
- 任何运行状态都能说明事实来源或明确“尚未开始”；
- Approval/Failure/Recovery 不被普通消息淹没；
- Knowledge context 提交前/提交后状态文案不同；
- 刷新、断线、浏览器后退不会创建重复 run；
- proposal 旧 revision 返回 409 时页面保留用户当前草稿并提示刷新；
- 1440、1728、390 无溢出、遮挡和伪造动画；
- Vitest 覆盖 Goal 空态、发送、proposal 审阅、恢复和 context receipt；
- 浏览器截图与 timeline fixture 能证明状态投影不是静态演示。

## 10. 成功指标

- 新用户从进入主对话到第一次成功发送的中位时间；
- Goal 确认率与从完成状态进入下一步的比例；
- Proposal 审阅完成率、冲突后安全恢复率；
- 运行失败后的恢复成功率；
- Knowledge 节点交接后形成有效主对话提问的比例；
- 用户在 Facts Rail 中找到下一步所需时间。
