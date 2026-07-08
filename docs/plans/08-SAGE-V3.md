# Sage v3 落地记录

> 日期：2026-07-08
> 当前阶段：方向一完成（ContextManager prompt caching）
> 参考：`docs/superpowers/prompts/2026-07-08-codex-goal-sage-v3.md`

## 目标

Sage v3 开始向 Hermes / Hermes Web UI 的设计演进。本阶段先做收益最大、风险最小的 P0：让 coding runtime 的 system prompt 在 session 生命周期内保持 byte-stable，给 DeepSeek/OpenAI/Claude 等提供商的隐式或显式 prompt caching 打基础。

## 本阶段改动

### ContextManager prompt caching

`core/coding/context_manager.py` 新增：

- `build_system_prompt_once()`：同一 tools 集合下复用缓存的 system prompt。
- `invalidate_system_prompt()`：压缩、记忆刷新或后续工具/skill 变化时显式失效。
- 三层 prompt 结构：
  - stable：Sage 身份、工具指引、工具列表。
  - context：当前 workspace repository 上下文。
  - volatile：日期精度的 session date。
- `normalize_text()`：对 user/history/tool 文本做 `.strip()`，保持 prompt 前缀稳定。
- `system_prompt_build_count`：测试和调试用，确认缓存是否生效。

### Runtime 生命周期修正

`core/coding/runtime.py` 现在在 session 初始化时创建一个 `self.context_manager`，并在每轮 `Engine` 里复用它。这样缓存生命周期从“单轮”提升到“session”。

### Compaction 失效点

`core/coding/compact.py` 的 `compact()` 支持可选 `context_manager` 参数。发生真实压缩时会调用 `invalidate_system_prompt()`，为后续 memory/context 刷新留出接入点。

## 测试覆盖

`tests/core/coding/test_context_compact.py` 新增：

- 同一 session 多轮 build 只构建一次 system prompt。
- invalidate 后下一轮重建。
- volatile tier 使用日期精度，不引入分钟/秒级 cache busting。
- compact 后能让 context cache 失效。

## 已验证

```bash
pytest tests/core/coding/test_context_compact.py -q
```

结果：`6 passed`

```bash
ruff check core/coding/context_manager.py core/coding/runtime.py core/coding/compact.py tests/core/coding/test_context_compact.py
mypy core/coding tests/core/coding/test_context_compact.py
```

结果：ruff 通过，mypy 通过。

```bash
pytest tests/core/coding/test_context_compact.py tests/core/coding/test_engine.py tests/api/test_coding_routes.py -q
```

结果：`22 passed`

## 后续方向

1. 工具系统重构：装饰器注册、工具拆文件、category / requires_approval 元数据。
2. Approval 系统：危险命令检测、pending approval 事件、前端 approval card。
3. Hermes Web UI 交互增强：工具结果截断、两阶段折叠防跳、文件树缓存、context ring tooltip、Skills 搜索分类。
4. Graphify 更新：完成 v3 主要方向后重新生成架构图谱。
