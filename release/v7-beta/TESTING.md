# Sage v7-beta Testing Entrypoint

## 快速验证（开发机）

```bash
# 后端全量
/Users/zeromadlife/anaconda3/bin/python -m pytest -q

# 后端定向（Harness + Knowledge + Coding）
/Users/zeromadlife/anaconda3/bin/python -m pytest tests/harness tests/core/coding tests/core/knowledge tests/api -q

# 静态检查
/Users/zeromadlife/anaconda3/bin/python -m ruff check .
/Users/zeromadlife/anaconda3/bin/python -m mypy core/ packages/sage_harness/ api/

# 前端
cd frontend && npm run test -- --run
cd frontend && npm run build
```

## 干净环境验证（CI 等价）

```bash
# 模拟 GitHub Actions 干净环境
uv venv --python 3.12 /tmp/sage-v7-verify
uv pip install --python /tmp/sage-v7-verify/bin/python -r requirements.txt
PYTHONPATH=. /tmp/sage-v7-verify/bin/python -m pytest -q
/tmp/sage-v7-verify/bin/python -m ruff check .
PYTHONPATH=. /tmp/sage-v7-verify/bin/python -m mypy core/ packages/sage_harness/ api/
```

## 群友试用前必须手跑的场景

### 场景 1：新用户首次进入

1. 用 GitHub OAuth 登录
2. 进入 `/assistant` 首页
3. 看到 today + composer + 示例 prompt
4. **验收**：5 秒内能看懂"Sage 是干嘛的"

### 场景 2：导入知识源 + 带引用问答

1. 连接一个 GitHub 仓库（如 `facebook/react`）
2. 等待索引完成（显示"已索引 N 个文档"）
3. 问"React Fiber 架构解决了什么问题？"
4. **验收**：回答带 `[来源: packages/react-reconciler/...]` 可点击引用

### 场景 3：多用户隔离

1. 用户 A 登录，创建 session，导入知识源
2. 用户 B 登录
3. **验收**：B 看不到 A 的任何 session / memory / file / workspace

### 场景 4：断线重连

1. 用户发起对话，工具执行中
2. 关闭浏览器
3. 5 秒后重新打开
4. **验收**：工具执行过程完整显示，不重复不丢失

### 场景 5：长会话压缩

1. 连续对话 20+ 轮
2. 观察 context 指示器
3. **验收**：达到 65% 自动压缩，用量下降，对话连续性不丢

### 场景 6：审批流程

1. 让 Sage 执行 `rm -rf node_modules` 之类危险命令
2. **验收**：弹出审批卡片，点"拒绝"后 Sage 收到拒绝结果继续

### 场景 7：三浏览器兼容

在 Chrome / Safari / Firefox 分别跑场景 1-2：
- **验收**：登录、对话、引用跳转不崩

### 场景 8：手机浏览器

在手机 Safari / Chrome 跑场景 1-2：
- **验收**：核心流程可操作，无横向滚动

## 已知不稳定点（群友试用时关注）

| 现象 | 原因 | 临时处理 |
| --- | --- | --- |
| 首次进入不知道干嘛 | onboarding 未实现 | 群友试用前必须补 |
| 知识源导入入口不显式 | 前端没有导入按钮 | 群友试用前必须补 |
| 长会话偶尔卡顿 | timeline 全量加载 | 刷新页面 |
| Safari 个别样式错位 | 只验证过 Chromium | 群友试用前手测 |
| Container Sandbox 未验证 | 服务器真实隔离未做 | 群友试用前用 OS 级隔离兜底 |
| `deerflow_v2` profile 关闭 | 对等矩阵未完成 | 默认 legacy runtime |

## Canary 部署可用性

- 部署 runbook：`docs/runbooks/09-Sage私有Canary部署.md`
- CI/CD runbook：`docs/runbooks/10-Sage本地CI-CD与Canary可用性.md`
- 健康探针：`b001441 fix(deploy): 复用无代理部署后健康探针`
- 回滚：`git revert` + 重新部署

## 反馈通道

- GitHub Issues：https://github.com/ZeroMadLife/sage-agent/issues
- 飞书群：群友试用群链接（发布时附上）
