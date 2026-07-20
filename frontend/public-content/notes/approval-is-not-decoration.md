---
title: 审批点不是 UI 装饰
date: 2026-07-19
summary: 真正需要确认的是会改代码、改知识、碰外部系统的操作，而不是所有按钮都弹窗。
tags: [harness, approval, safety]
related:
  - label: Practice Engine
    href: https://github.com/ZeroMadLife/sage-agent/tree/dev/sage-v7/core/coding
---

## 错误做法

把“确认”做成每个工具调用前的仪式按钮。用户很快会疲劳点击，真正危险的操作反而被淹没。

## Sage 的边界

审批服务的是**副作用边界**：

- 写文件 / patch
- 可能破坏工作区的 shell
- 改变长期知识的提案
- 触及外部系统的动作

只读检索、解释、规划不应被同等对待。

## 可验证信号

公开站不会宣称“已经是生产级多租户安全”。它只展示：

- 审批点存在于运行时路径
- timeline 能记录批准与拒绝
- 公开 Ask Sage 仍然没有写权限
