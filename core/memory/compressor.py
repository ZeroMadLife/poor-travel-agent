"""Context compression for long-running chat sessions."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

Message = dict[str, str]

SUMMARY_PROMPT = """请将以下对话历史压缩为简洁摘要，保留：
- 用户的核心需求（目的地/预算/偏好/日期）
- Agent 的关键决策和推荐
- 已确认的行程要点
- 用户反馈和调整要求

只输出摘要内容，不要其他文字。
"""


class ContextCompressor:
    """上下文压缩器 — 防止对话历史 token 爆炸。

    策略参考 Claude Code auto-compact：
    system prompt 保留，旧消息压缩成摘要，最近若干轮保留完整内容。
    """

    def __init__(
        self,
        llm: Any,
        max_tokens: int = 6000,
        keep_recent_turns: int = 6,
    ) -> None:
        self._llm = llm
        self.max_tokens = max_tokens
        self.keep_recent_turns = keep_recent_turns

    def estimate_tokens(self, messages: list[Message]) -> int:
        """估算消息列表 token 数（近似：字符数 / 3）。"""
        total_chars = sum(len(message.get("content", "")) for message in messages)
        return total_chars // 3

    def should_compress(self, messages: list[Message]) -> bool:
        """判断是否需要压缩。"""
        return self.estimate_tokens(messages) > self.max_tokens

    async def compress(self, messages: list[Message]) -> list[Message]:
        """压缩旧消息，保留 system prompt 和最近几轮完整对话。"""
        if not messages:
            return []

        keep_count = self.keep_recent_turns * 2
        system_messages = [message for message in messages if message.get("role") == "system"]
        non_system_messages = [message for message in messages if message.get("role") != "system"]
        if len(non_system_messages) <= keep_count:
            return messages

        old_messages = non_system_messages[:-keep_count]
        recent_messages = non_system_messages[-keep_count:]
        conversation_text = "\n".join(
            f"{message.get('role', '')}: {message.get('content', '')}" for message in old_messages
        )
        prompt = f"{SUMMARY_PROMPT}\n\n{conversation_text}"

        try:
            response = await self._llm.ainvoke([{"role": "user", "content": prompt}])
            summary_content: object = getattr(response, "content", response)
            summary_text = (
                summary_content if isinstance(summary_content, str) else str(summary_content)
            )
        except Exception as exc:
            logger.warning("Context compression failed: %s", exc)
            return messages

        summary_message = {"role": "system", "content": f"[对话摘要] {summary_text}"}
        return [*system_messages, summary_message, *recent_messages]
