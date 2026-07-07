# TourSwarm — 旅游 Agent + Sage Web Coding 助手

> 一个本地 Agent 实验仓：旅游侧沉淀"个人旅游助手"产品原型，Coding 侧（Sage）沉淀"网页端自主编程助手"框架能力。当前阶段不是上线运营，而是把 demo 打磨成能讲清楚架构、能真实联调、能继续量化评测的作品。

## 当前定位

| 维度 | 说明 |
|------|------|
| 产品方向 | 个人旅游 Agent + Sage 网页端 Coding Agent |
| 旅游侧差异化 | ReAct 主Agent + `generate_itinerary` 工具包装多Agent图 + 自研 MCP 工具 + 预算约束 + 记忆/验证器 |
| Sage 差异化 | Pico v3 风格 Runtime + XML 工具协议 + Skills 系统 + 文件/搜索/patch/shell 工具 + 两层权限治理 + 三栏布局 + WebSocket 流式 |
| 当前阶段 | Sage v2：三栏布局 + Skills + 文件树 + git 状态 + 模型选择 + 工具折叠 |
| 技术栈 | FastAPI + WebSocket + LangChain ReAct + LangGraph + MCP + Mem0/Qdrant + Redis + Vue3 + TypeScript + Pinia |
| 语言 | Python 3.11+ / TypeScript |

## 核心架构

### 旅游助手

Phase 4 之前是“用户输入 -> 多Agent图 -> 一次性行程”。Phase 4.5 改成两段式个人助手：

```text
Vue3 Chat UI
  -> POST /api/v1/chat 创建 session
  -> WebSocket /api/v1/chat/{session_id}/stream 长连接多轮对话
  -> FastAPI
  -> TourAgent 主Agent（ReAct, DeepSeek）
       ├─ 普通聊天：直接回复
       ├─ 附近查询：search_nearby / get_poi_detail / geocode / get_route
       ├─ 天气查询：get_weather / get_forecast
       ├─ 景点查询：search_attractions / search_scenic_spots / get_scenic_detail
       └─ 复杂规划：generate_itinerary 工具
              -> LangGraph 多Agent图
                   -> Info Agent + Recommend Agent
                   -> Planning Agent
                   -> Budget Agent
              -> 结构化 Itinerary
```

主Agent只知道自己调用了一个叫 `generate_itinerary` 的工具；工具内部才启动 Phase 2 的多Agent协作。这让产品体验更像“个人助手”，而不是每次都强行跑完整规划流。

### Coding 助手

Coding Agent v1 参考本机 Pico v3 的 runtime/tools/engine 架构，但外壳换成 TourSwarm 的 FastAPI + Vue3：

```text
Vue3 CodeAssist UI
  -> POST /api/v1/coding/session 创建 coding session
  -> WebSocket /api/v1/coding/{session_id}/stream 长连接收发任务
  -> FastAPI api/coding.py
  -> CodingRuntime
       ├─ WorkspaceContext：工作目录、路径安全、输出截断
       ├─ Tool Registry：list_files / read_file / search / run_shell / write_file / patch_file
       ├─ PermissionChecker + ToolPolicyChecker：写权限、plan mode、patch 前 fresh read、shell 搜索拦截
       ├─ Engine：model -> parse <tool>/<final> -> execute tool -> stream event
       ├─ ContextManager + CompactManager：上下文预算与历史压缩
       ├─ Todo / Plan Mode / Worker：任务账本、只读规划、子 agent
       └─ .coding/：session events 与 run trace 本地持久化
```

Coding 侧是新增能力，和旅游侧 `agents/`、`mcp_servers/`、`core/verifier.py`、`evals/` 隔离。

## Phase 4.5 本轮变动

| 任务 | 模块 | 提交 |
|------|------|------|
| 高德周边搜索工具 | `mcp_servers/amap/client.py`, `server.py` 新增 `search_nearby` / `get_poi_detail` | `e84d662` |
| LLM 意图理解 | `core/intent.py`，替代旧的硬编码 `parse_input` 思路 | `be66de4` |
| 行程生成工具 | `agents/itinerary_tool.py`，把 LangGraph 多Agent图包装成 `generate_itinerary` | `7f013b4` |
| ReAct 主Agent | `agents/react_agent.py`，负责日常对话、工具选择和多轮上下文 | `d51aa4b` |
| API 两段式接入 | `api/main.py`, `api/ws.py`, `api/services/chat_runner.py`，长连接多轮 WebSocket | `55f00de` |
| 前端聊天界面 | `frontend/src/views/ChatView.vue` 与消息/工具/行程组件 | `5b56f5e` |
| 验收适配 | API/集成测试适配新 Agent API | `380b232`, `226416f` |

详细计划见 `docs/plans/04.5-PHASE4.5-AGENT-EXPERIENCE.md`。

## Phase 6 Coding Agent v1

| 层 | 模块 | 说明 |
|----|------|------|
| Layer 0-2 | `core/coding/workspace.py`, `tools/`, `permissions.py`, `tool_policy.py` | 路径安全、6 个核心工具、权限与策略治理 |
| Layer 3-4 | `engine.py`, `engine_helpers.py`, `model_output.py`, `context_manager.py`, `compact.py` | XML 工具协议、流式 engine、上下文预算和压缩 |
| Layer 5-8 | `todo_ledger.py`, `plan_mode.py`, `worker_*`, `runtime.py`, `session_*`, `run_store.py` | todo、plan mode、worker、session/event/run trace 持久化 |
| Layer 9 | `api/coding.py`, `api/main.py`, `api/schemas.py` | Coding REST session + WebSocket 流式接口 |
| Layer 10 | `frontend/src/views/CodingView.vue`, `frontend/src/api/coding.ts` | 浏览器中的 CodeAssist 最小可用界面 |

详细落地记录见 `docs/plans/06-CODING-AGENT-V1.md`。

## 仓库结构

```text
tour-agent/
├── agents/
│   ├── react_agent.py          # ReAct 主Agent
│   ├── itinerary_tool.py       # generate_itinerary 工具
│   └── graph.py                # Phase 2 多Agent图
├── api/                        # FastAPI + 旅游/Coding WebSocket
├── core/
│   ├── coding/                 # Coding Agent runtime/tools/engine
│   ├── intent.py               # LLM 意图解析
│   ├── memory/                 # Redis 短期记忆 + Mem0 长期记忆
│   └── verifier.py             # 行程确定性验证器
├── mcp_servers/                # 高德 / 天气 / 景点 MCP Server
├── frontend/                   # Vue3 聊天界面
├── evals/                      # 旅行 case 与评测脚本
├── tests/                      # 单元 / 集成 / 性能测试
├── docker-compose.yml          # 本地 PostgreSQL + Redis + Qdrant
├── requirements.txt
└── .env.example
```

## 本地启动文档

### 1. 第一次准备环境

```bash
cd /Users/zeromadlife/Desktop/tour-agent

conda create -n tourswarm python=3.11 -y
conda activate tourswarm

python -m pip install --upgrade pip
pip install -r requirements.txt

cd frontend
npm install
cd ..

cp .env.example .env
```

### 2. 配置 `.env`

完整联调至少需要 LLM Key。旅游主Agent和 Coding 助手目前都默认使用 DeepSeek：

```bash
# 旅游主Agent + Coding助手
DEEPSEEK_API_KEY=你的deepseek_key

# 复杂行程规划默认用 LLM_MODEL 指向的模型；默认是豆包
LLM_MODEL=doubao:Doubao-Seed-2.0-pro
DOUBAO_API_KEY=你的豆包_key
```

如果你暂时只想用 DeepSeek 跑通，可以把规划模型也切到 DeepSeek：

```bash
LLM_MODEL=deepseek:deepseek-chat
DEEPSEEK_API_KEY=你的deepseek_key
```

附近搜索需要高德 Key：

```bash
AMAP_API_KEY=你的高德_web服务_key
```

天气查询需要和风天气 Key；如果不配，行程规划会按天气失败降级继续跑：

```bash
QWEATHER_API_KEY=你的和风_key
QWEATHER_BASE_URL=https://你的host.re.qweatherapi.com/v7
QWEATHER_GEO_URL=https://你的host.re.qweatherapi.com/geoapi/v2
```

### 3. 每次启动中间件

```bash
cd /Users/zeromadlife/Desktop/tour-agent
docker compose up -d
docker compose ps
```

确认 `tourswarm-postgres`、`tourswarm-redis`、`tourswarm-qdrant` 都是 `Up` 或 `healthy`。

### 4. 启动后端

```bash
cd /Users/zeromadlife/Desktop/tour-agent
conda activate tourswarm
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload --env-file .env
```

自检：

```bash
curl http://127.0.0.1:8000/health
```

返回 `{"status":"ok"}` 只代表 FastAPI 活着。若 WebSocket 返回 `Agent is not configured`，优先检查 `DEEPSEEK_API_KEY` 和 `LLM_MODEL` 对应的 Key 是否被 `--env-file .env` 加载进进程。

Coding 助手在创建 session 时才实例化模型。如果点“代码”后创建 session 失败，优先检查同一个后端进程是否读到了 `DEEPSEEK_API_KEY`。

如果 8000 被占用：

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

可以停掉旧进程，或把 TourSwarm 改到 8010：

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8010 --reload --env-file .env
```

### 5. 启动前端

```bash
cd /Users/zeromadlife/Desktop/tour-agent/frontend
VITE_API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev
```

打开 Vite 输出地址，通常是：

```text
http://127.0.0.1:5173/
```

本地开发推荐只设置 `VITE_API_PROXY_TARGET`，让 Vite 代理 `/api` 和 WebSocket 到后端。不要优先设置 `VITE_API_BASE_URL=http://127.0.0.1:8000`，否则容易遇到浏览器 CORS 问题。

如果后端换成 8010，前端对应改成：

```bash
VITE_API_PROXY_TARGET=http://127.0.0.1:8010 npm run dev
```

页面顶部有两个入口：

| 入口 | 用途 | 后端接口 |
|------|------|----------|
| 旅行 | 旅游问答、天气、附近搜索、复杂行程规划 | `/api/v1/chat`, `/api/v1/chat/{session_id}/stream` |
| 代码 | 读文件、搜索、改文件、跑命令的网页端 Coding 助手 | `/api/v1/coding/session`, `/api/v1/coding/{session_id}/stream` |

### 6. 推荐联调输入

旅游助手：

```text
你好
```

```text
帮我规划杭州2日游预算500元，喜欢美食和自然风光
```

```text
杭州明天天气怎么样
```

```text
附近有什么好吃的
```

注意：“附近有什么好吃的”要真正返回高德周边结果，需要主Agent拿到经纬度。当前前端还没有浏览器定位能力，所以这是下一步产品化要补的点；现在可通过更明确的位置/地址类输入辅助 Agent 调 `geocode`。

Coding 助手：

```text
读 README.md 告诉我项目叫什么
```

```text
搜索 core/coding 里哪里定义了 patch_file
```

```text
读 api/coding.py，总结 Coding WebSocket 的事件流
```

Coding 助手的事件、session 和 run trace 会写到仓库根目录的 `.coding/`：

```text
.coding/sessions/<session_id>.json
.coding/sessions/<session_id>.events.jsonl
.coding/runs/<run_id>/trace.jsonl
```

## PyCharm 启动

### 后端 Run Configuration

| 配置项 | 值 |
|--------|-----|
| Type | Python |
| Module name | `uvicorn` |
| Parameters | `api.main:app --host 127.0.0.1 --port 8000 --reload --env-file .env` |
| Working directory | `/Users/zeromadlife/Desktop/tour-agent` |
| Interpreter | conda env `tourswarm` |

PyCharm 启动前仍然要先执行：

```bash
docker compose up -d
```

### 前端 Run Configuration

推荐直接用 PyCharm Terminal：

```bash
cd /Users/zeromadlife/Desktop/tour-agent/frontend
VITE_API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev
```

也可以建 npm 配置：

| 配置项 | 值 |
|--------|-----|
| package.json | `/Users/zeromadlife/Desktop/tour-agent/frontend/package.json` |
| Command | `run` |
| Scripts | `dev` |
| Environment variables | `VITE_API_PROXY_TARGET=http://127.0.0.1:8000` |

## 质量检查

```bash
cd /Users/zeromadlife/Desktop/tour-agent
bash scripts/check.sh

cd frontend
npm run test -- --run
npm run build
```

Coding 模块可单独快速检查：

```bash
pytest tests/core/coding tests/api/test_coding_routes.py -q
```

测试使用 Mock，不消耗真实 API 额度；本地联调才需要真实 Key。

## 常见问题

| 现象 | 优先检查 |
|------|----------|
| `Address already in use` | `lsof -nP -iTCP:8000 -sTCP:LISTEN` 查占用，换端口或杀旧进程 |
| `/health` 正常但聊天失败 | 后端 Agent 构建失败，检查 `DEEPSEEK_API_KEY`、`LLM_MODEL`、`DOUBAO_API_KEY` |
| WebSocket 返回 `Agent is not configured` | `.env` 没加载或 LLM Key 缺失 |
| 创建 Coding session 失败 | 后端进程没有读到 `DEEPSEEK_API_KEY`，或 `.env` 被放在了错误目录 |
| 前端页面能开但发消息失败 | 后端端口和 `VITE_API_PROXY_TARGET` 不一致 |
| CodeAssist 连接中不动 | 后端 `/api/v1/coding/session` 失败，打开浏览器 Network 或后端日志看 500 详情 |
| Coding 工具被拒绝 | 可能触发了路径逃逸、plan mode、patch 前未 read、或 shell 搜索拦截策略 |
| 天气失败但仍生成行程 | 正常降级；补和风 Key 和 Host 可恢复真实天气 |
| 附近搜索结果不稳定 | 高德 Key、经纬度、当前位置输入是否明确 |

## 当前边界

- 前端是聊天 demo，不是最终 UI。
- 旅游会话状态仍以内存/本地服务为主；Coding 会话会落 `.coding/`，但还不是多人协作存储。
- 没有登录、地图、分享、UniApp、线上部署。
- `generate_itinerary` 已经能包装多Agent图，但工具级流式进度还比较粗。
- Coding 助手具备最小可用的读/搜/改/跑命令能力，但还没有人工审批 UI、diff 预览、sandbox、RAG 和 benchmark。
- 下一阶段重点不是堆 UI，而是补定位输入、评测指标、错误降级、可观测性，以及 Coding Agent 的任务成功率量化。

## License

MIT
