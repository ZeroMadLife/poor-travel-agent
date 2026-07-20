# Sage H2.7A Thread Goal 与手动续跑实施计划

## 目标

在唯一 Chat Harness runtime 上补齐 session 级 Thread Goal，使一个 Thread 同时最多只有一个 primary Goal，并让用户显式选择“继续目标”。本阶段只交付可恢复、可审计的目标状态机，不自动续跑，不使用模型自评分，也不写入 Mastery Ledger。

## 契约

1. Goal 以 revisioned Harness 事件持久化到现有 `SessionEventJournal`，不建立第二套会话数据库。
2. 创建、修改、清除和评估都使用 `expected_revision` CAS；旧页面不能覆盖新目标。
3. 每个 run 开始时冻结当前 Goal 快照，并同时写入 `run_started` receipt 与 DeerFlow durable context。
4. approval 恢复继续使用该 run 已冻结的 Goal，不读取 session 的最新 Goal。
5. Goal 评估只读取公开 timeline 终态与证据引用，返回 `satisfied | blocked | continue`、typed blocker、evidence refs 和 next action；本阶段的确定性评估不会自行宣称 satisfied。
6. 用户点击“继续目标”时先校验 Goal revision，再通过现有 WebSocket 和 RunCoordinator 启动普通 run；不新建执行通道。
7. Goal 默认关闭。没有 Goal 时，现有对话行为保持不变。

## 切片

1. Journal：revisioned Goal event、恢复投影、run-frozen receipt。
2. Harness：Goal domain service、确定性评估、durable context 投影。
3. API：Goal get/upsert/clear/evaluate/continue，WebSocket revision guard。
4. 前端：共享 Coding store 加载 Goal；工作台提供创建、评估、继续和清除的最小控制面。
5. 验证：定向后端、全量后端、前端测试、生产构建、`git diff --check`、Browser 真实会话与恢复。

## 明确留到 H2.7B/H2.7C

- post-turn LLM evaluator 与安全自动续跑。
- Mastery Ledger、能力权重和可验证掌握度。
- Goal 自动拆解、学习计划批准和长期 Proposal。
- 公开 HR Agent 的独立资料集、限流与泄漏防护。
