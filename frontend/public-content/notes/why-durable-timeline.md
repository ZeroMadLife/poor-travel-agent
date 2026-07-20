---
title: 为什么 Harness 需要 durable timeline
date: 2026-07-20
summary: 刷新后如何证明副作用已经发生，而不是重新编造一轮模型状态。
tags: [harness, timeline]
related:
  - label: packages/sage_harness
    href: https://github.com/ZeroMadLife/sage-agent/tree/dev/sage-v7/packages/sage_harness
---

## 问题

Agent 界面最容易骗人的地方，不是回答内容，而是**状态恢复**。

刷新、断线、审批后继续跑——如果 UI 只靠前端内存或临时 stream 缓存，用户看到的“已执行 / 已写入 / 已通过”可能根本无法证明。

## 取舍

Sage 把 plan、tool、approval、reply、terminal 统一投影到 **durable timeline**。

- UI 的事实源是 timeline，不是模型临时输出
- 审批点挂在同一条运行路径上
- 恢复时回放已经发生的事件，而不是重新生成“看起来差不多”的状态

## 为什么这算工程落地

这不是多画一个 loading，也不是给聊天框加几个图标。它要求：

1. 事件可持久化
2. 投影可去重
3. 危险操作有明确 gate
4. 前端与审计共享同一事实

这也是公开站把 Harness 放在首页核心证据区的原因。
