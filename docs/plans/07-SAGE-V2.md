# Sage v2 落地记录

> 日期：2026-07-07
> 分支：feat/coding-agent-v1
> 前置：v1（commit `d966b1a`）已完成 Pico 架构移植

## 目标

项目正式更名 **Sage**。v2 把前端从"能跑"升级到"好用"，对标 Hermes WebUI 核心体验，并补齐 Skills 系统。

## 交付物

### 阶段 1：后端 Skills 系统 + API + system prompt

| 文件 | 改动 |
|------|------|
| `core/coding/skills/skill.py` | Skill dataclass + frontmatter 解析 + slash 命令解析 |
| `core/coding/skills/registry.py` | SkillRegistry：发现/加载/解析（builtin→user→project） |
| `core/coding/skills/bundled/{review,test,commit}/SKILL.md` | 3 个内置 skill |
| `core/coding/context_manager.py` | system prompt 改为 Sage 人设 |
| `core/coding/runtime.py` | 接入 SkillRegistry + list_files/read_file/git_status/switch_model |
| `api/coding.py` | 新增 7 个 REST 端点 + WebSocket slash 命令处理 |
| `api/schemas.py` | 新增 10 个 coding 相关请求/响应模型 |
| `tests/core/coding/test_skills.py` | 11 个 skills 测试 |
| `tests/api/test_coding_routes.py` | 新增 12 个 API 端点测试 |

新增 API 端点：
- `GET /api/v1/coding/{session_id}/files` — 文件树
- `GET /api/v1/coding/{session_id}/file` — 文件内容
- `GET /api/v1/coding/{session_id}/git/status` — git 状态
- `GET /api/v1/coding/models` — 模型列表
- `PATCH /api/v1/coding/{session_id}/model` — 切换模型
- `GET /api/v1/coding/skills` — skill 列表
- `GET /api/v1/coding/skills/{name}` — skill 详情
- `GET /api/v1/coding/mcp/servers` — MCP 配置状态

### 阶段 2-5：前端三栏布局 + 全部交互

| 文件 | 改动 |
|------|------|
| `frontend/src/views/CodingView.vue` | 从单栏重构为三栏布局 |
| `frontend/src/stores/coding.ts` | 新增 Pinia store（会话/工具/文件/git/skills/模型） |
| `frontend/src/components/CodingSidebar.vue` | 左栏：Skills + MCP + 模型列表 |
| `frontend/src/components/CodingFileTree.vue` | 右栏：文件树 + 面包屑 + 预览 |
| `frontend/src/components/CodingGitBadge.vue` | 顶栏：branch + dirty 数 |
| `frontend/src/components/CodingToolActivity.vue` | 工具调用折叠 + 两阶段渲染 |
| `frontend/src/components/CodingComposer.vue` | composer footer：模型选择 + context 环 + send |
| `frontend/src/api/coding.ts` | 新增 9 个 API 调用函数 |
| `frontend/src/types/api.ts` | 新增 10 个类型定义 |
| `frontend/src/App.vue` | 导航改 Sage 品牌，coding 模式全屏 |
| `frontend/src/stores/coding.test.ts` | 6 个 store 测试 |

### 设计哲学落地（对标 Hermes）

| Hermes 设计 | Sage 实现 |
|-------------|-----------|
| 工具调用是 metadata 不是 message | CodingToolActivity 默认折叠 `Activity: N tools` |
| 两阶段渲染（live/settled） | 运行中可展开看进度，settled 后自动收起 |
| Composer footer 集中会话作用域控件 | model 选择 + context 环 + send 全在 footer |
| 圆形 context 用量环 | SVG 环形，<60% 绿 / 60-80% 黄 / >80% 红 |
| 文件树 + git badge | 右栏文件树 + 面包屑 + 顶栏 branch+dirty |
| Skills/MCP 管理面板 | 左栏 Skills（展开/使用）+ MCP 状态 + 模型列表 |
| inline error 处理 | error 事件显示在消息区 |

## 验收记录

| 命令 | 结果 |
|------|------|
| `bash scripts/check.sh` | ruff + format + mypy + **297 pytest passed** |
| `cd frontend && npm run test -- --run` | **23 tests passed**（12 files） |
| `cd frontend && npm run build` | passed（208KB JS / 22KB CSS） |

- 旅游侧测试零回归
- 前端 build 通过
- system prompt 已改为 Sage 人设

## 三个内置 Skills

- `/review` — 代码审查（git diff → 逐文件分析 → 审查结论）
- `/test` — 跑测试（scripts/check.sh 或 pytest → 分析失败 → 修复建议）
- `/commit` — 准备 commit（git status/diff → 总结 → conventional commits 消息建议）

## 后续优化

- prompt caching 优化（system_prompt + tools 做 byte-stable 前缀）
- approval UI（risky 工具 pending 状态 + 前端 allow/deny）
- diff 预览（patch/write 前后展示变更）
- Skill 调用统计
- slash 命令自动补全下拉
- 文件编辑功能（当前只读预览）
- MCP 实际连接状态探测（当前只读配置）
