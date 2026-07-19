# Sage v7-beta Release Pack

本目录把 v7-beta 群友试用版的发布材料集中在一处。产品面向文档留在 `docs/`，发布证据、评审记录和学习笔记在这里。

## 目录内容

| 路径 | 用途 |
| --- | --- |
| `release/v7-beta/CHANGELOG.md` | v7-beta 变更摘要与发布说明 |
| `release/v7-beta/TESTING.md` | 测试入口、重跑命令、群友试用前必须手跑的场景 |
| `release/v7-beta/REVIEW.md` | 评审包：产品定位、架构图、Harness 边界、证据、安全审查 |
| `release/v7-beta/README.md` | 本文件 |
| `release/v7-beta/learning/` | v7-beta 阶段学习笔记（后续沉淀） |

## 阅读顺序

1. **先读 `CHANGELOG.md`**：了解本版交付了什么、改了什么、已知限制
2. **读 `TESTING.md`**：了解怎么验证、群友试用前必须跑哪些场景
3. **用 `REVIEW.md`**：做架构评审、安全审查、证据回放
4. **`learning/`**：深入学习 v7-beta 架构与设计决策（后续沉淀）

## 群友试用前的硬阻塞项

以下三项必须完成，否则不发群：

1. **onboarding 引导**：新用户首次登录走 3 步（你是谁 -> 连知识源 -> 问第一个问题）
2. **知识源导入入口**：GitHub 仓库导入 + Obsidian zip 上传，前端显式入口
3. **多用户隔离验证**：A 用户看不到 B 用户任何数据

## 群友试用阶段不做

- Loop Engineer 自动化开发
- Dream 自动反思
- AST 知识图谱 / Local Companion
- `deerflow_v2` 默认切换
- Wiki 自动更新
- 完整对等矩阵

## 相关资料

- 设计书：`docs/superpowers/specs/2026-07-15-sage-v7-personal-assistant-knowledge-evolution-design.md`
- DeerFlow 迁移设计：`docs/superpowers/specs/2026-07-16-sage-deerflow-harness-migration-design.md`
- Loop Engineer 设计：`docs/superpowers/specs/2026-07-16-sage-loop-engineer-harness-design.md`
- Obsidian 学习库：`Obsidian-Knowledge-Base/03_项目/tourswarm/技术沉淀/sage-learning/`
- 部署 runbook：`docs/runbooks/09-Sage私有Canary部署.md` / `10-Sage本地CI-CD与Canary可用性.md`

## 版本事实

- 分支：`dev/sage-v7`（领先 `main` 72 个 commit）
- 本地联调 HEAD（2026-07-19）：`4479ad2 feat(frontend): 完成目标驱动产品壳层`
- 后端测试：1644 passed
- 前端测试：59 files / 436 tests passed
- mypy：264 source files 通过
- GitHub CI：`backend-quality` / `frontend-quality` / `python` 全绿
- 状态：**beta，不保证生产稳定**
