# Sage 页面 PRD 索引

这组 PRD 把产品方向拆成可实现、可验收的页面职责。它们依赖总规格 [2026-07-22 Sage UI Product Convergence Design](../../superpowers/specs/2026-07-22-sage-ui-product-convergence-design.md) 和视觉规则 [style.md](../style.md)。

| 页面 | 主要问题 | 入口 |
| --- | --- | --- |
| [主对话](main-conversation.md) | 我现在要做什么，Sage 做到了哪一步 | `/assistant`、`/coding/session/:sessionId` |
| [Knowledge](knowledge.md) | 我的知识库是什么结构，下一步研究哪个缺口 | `/knowledge` |
| [设置与记忆](settings-memory.md) | 系统如何运行，哪些长期信息已经保存 | `/settings/:section?` |
| [公开门面](public-profile.md) | 外部访客如何理解项目和验证工程能力 | `/public`、独立 public build |

Growth 不再作为主页面 PRD；私人进度由主对话 Goal/Evidence 承载，公开成长由公开门面承载。
