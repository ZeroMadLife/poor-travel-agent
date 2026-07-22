# 公开门面 PRD

## 1. 页面目标

让 HR 或外部访客通过一个公网地址，在三分钟内理解 Sage 的产品命题、工程能力和可验证进度，并能用一个受限的 Ask Sage 入口探索公开内容。

这是外部展示页，不是私人工作台，也不是主 Harness 的匿名代理。

## 2. 访客任务

1. 理解 Sage 是什么，以及为什么不只是聊天框；
2. 查看目标驱动、Harness、Knowledge、Evidence 等代表性工程案例；
3. 阅读技术笔记或公开成长记录；
4. 询问公开资料并看到 citation/evidence；
5. 跳转 GitHub、简历和联系方式。

## 3. 范围

### 包含

- 清晰的项目定位和个人介绍；
- 2-4 个可展开工程案例；
- 公开文章/笔记列表；
- 证据型成长时间线；
- 受限 Ask Sage，使用独立公开资料集；
- 移动端阅读、键盘导航、固定外部链接。

### 不包含

- 私人 Goal、Session、Memory、Knowledge、Workspace、文件或代码写入；
- 公开页调用 shell/write/私有 MCP/个人 provider；
- 公开页伪造实时运行、工具调用或个人成长百分比；
- 公开访客直接批准任何 proposal；
- 在没有独立公开 Agent 契约时连接主对话 runtime。

## 4. 页面结构

```text
Header
  ├─ Sage / identity
  ├─ Work / Writing / Path anchors
  └─ GitHub / Contact
Intro
  ├─ one-sentence product thesis
  └─ open project / ask sage
Selected Work
  ├─ Goal Contract
  ├─ Harness 2.0
  ├─ Knowledge Surface
  └─ Mastery Evidence
Writing / Notes
Learning Path
Ask Sage drawer
Footer / public boundary
```

第一屏必须让访客看到产品/项目主体，不以大段营销标语或装饰图替代内容。

## 5. Ask Sage

### 当前阶段

- 模式：`static` 或明确声明的受限公开 Agent；
- corpus：已批准公开文章、工程说明和项目摘要；
- 返回：回答 + 可点击公开 evidence；
- 私人数据：永不进入请求；
- connect-src：保持静态构建的安全边界，未开放后端时使用确定性本地匹配。

### 未来开放 Agent

必须具备独立 `surface`、`capability_id`、owner/tenant 隔离、限流、usage 账本和 evidence citation。任何写入操作必须走 proposal/approval，不能复用私人主对话权限。

### 状态

| 状态 | 反馈 |
| --- | --- |
| 空 | 提供 3 个公开问题示例 |
| 查询中 | 明确“正在查询公开资料”，不展示伪造工具步骤 |
| 有回答 | 回答 + evidence/source chips |
| 无匹配 | 说明公开范围，不暴露私有边界细节 |
| 失败/限流 | 可重试和公开说明，不泄露后端配置 |

## 6. 视觉与交互

公开门面可使用 Soft Precision 的中性底、Sage 绿、蓝色证据和少量滚动 reveal，但内容优先：

- 不做纯装饰渐变球；
- 不把整个页面做成私人后台；
- 卡片用于代表性项目和文章，不做多层嵌套；
- 长内容点击展开，默认只显示可扫描摘要；
- Ask Sage 使用右侧 drawer 或移动端 bottom sheet，阅读位置不丢失；
- 外部链接具备清晰 icon 和新窗口/同窗口语义。

## 7. 内容治理

- 公开内容必须明确标记版本/日期；
- 每个工程案例至少有“问题、取舍、证据、边界”四项；
- 文章可以由 Agent/Codex 起草，但发布前需人工确认；
- 个人私密路径、token、内部日志、未公开仓库和未经批准截图禁止进入 public corpus；
- 内容发布和撤下都有可追踪记录。

## 8. 响应式

### 桌面

- 首屏主体、导航和 Ask Sage 入口在 `1440x900` 内可见；
- 项目案例采用单层纵向叙事，避免四列卡片墙；
- 页面可通过 anchor 快速跳到 Work/Writing/Path。

### 移动

- 文章正文 `16px` 左右内边距；
- Ask Sage drawer 变为 full-width bottom sheet；
- 证据 chips 可以横向滚动，但核心回答不横向溢出；
- 外部链接和 CTA 至少 `44px` 高。

## 9. 契约依赖

- 独立公开资料集和发布版本；
- public Agent 的只读检索和 citation；
- 内容发布、撤下、版本和缓存策略；
- 公网安全 headers、CSP、限流和错误页；
- 公开域名/HTTPS/部署探针。

## 10. 验收标准

- 未登录访客可以直接打开公网地址，不被私人登录挡住；
- 3 分钟内能找到项目定位、代表作品、技术笔记和联系方式；
- Ask Sage 只返回公开资料，且有来源或明确无匹配说明；
- 任意私有内容不会被页面资源、构建产物、回答或错误日志引用；
- 1440、1728、390 无遮挡、横向溢出和控制台错误；
- 页面无伪造运行状态和“已经接入后端”的错误暗示；
- 独立 public build 保持 `connect-src` 和安全边界不被私人应用改动。

## 11. 成功指标

- 首屏停留与 Work/Writing/Path 点击率；
- HR 阅读到 GitHub/联系入口的转化；
- Ask Sage 首次提问成功率和 evidence 点击率；
- 移动端可读完成率；
- 发布后内容撤回/隐私问题为零。
