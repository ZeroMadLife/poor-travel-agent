"""Context compressor tests."""

from unittest.mock import AsyncMock, MagicMock

from core.memory.compressor import ContextCompressor


def test_estimate_tokens_uses_character_approximation() -> None:
    """Token estimation should use an inexpensive chars / 3 approximation."""
    compressor = ContextCompressor(llm=MagicMock())
    messages = [
        {"role": "user", "content": "abcdef"},
        {"role": "assistant", "content": "abcdef"},
    ]

    assert compressor.estimate_tokens(messages) == 4


def test_should_compress_under_threshold() -> None:
    """Small histories should not be compressed."""
    compressor = ContextCompressor(llm=MagicMock(), max_tokens=100)

    assert compressor.should_compress([{"role": "user", "content": "hello"}]) is False


def test_should_compress_over_threshold() -> None:
    """Large histories should trigger compression."""
    compressor = ContextCompressor(llm=MagicMock(), max_tokens=3)

    assert compressor.should_compress([{"role": "user", "content": "x" * 30}]) is True


async def test_compress_preserves_system_and_recent_messages() -> None:
    """Compression should preserve the system prompt and recent conversation window."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="用户想去杭州，预算500元"))
    compressor = ContextCompressor(llm=llm, max_tokens=1, keep_recent_turns=2)
    messages = [
        {"role": "system", "content": "系统提示"},
        *[
            {"role": "user" if index % 2 == 0 else "assistant", "content": f"消息{index}"}
            for index in range(8)
        ],
    ]

    compressed = await compressor.compress(messages)

    assert compressed[0] == {"role": "system", "content": "系统提示"}
    assert compressed[1]["role"] == "system"
    assert "对话摘要" in compressed[1]["content"]
    assert compressed[-4:] == messages[-4:]
    assert len(compressed) == 6


async def test_compress_uses_llm_summary_prompt() -> None:
    """Old messages should be sent to the LLM summary prompt."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="用户喜欢博物馆"))
    compressor = ContextCompressor(llm=llm, max_tokens=1, keep_recent_turns=1)
    messages = [
        {"role": "user", "content": "我喜欢博物馆"},
        {"role": "assistant", "content": "已记录"},
        {"role": "user", "content": "明天去杭州"},
        {"role": "assistant", "content": "好的"},
    ]

    compressed = await compressor.compress(messages)

    prompt_messages = llm.ainvoke.await_args.args[0]
    assert "我喜欢博物馆" in prompt_messages[0]["content"]
    assert "用户喜欢博物馆" in compressed[0]["content"]
    assert compressed[-2:] == messages[-2:]


async def test_compress_handles_llm_error() -> None:
    """LLM failures should keep the original messages intact."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(side_effect=Exception("llm unavailable"))
    compressor = ContextCompressor(llm=llm, max_tokens=1, keep_recent_turns=1)
    messages = [{"role": "user", "content": "x" * 30}]

    compressed = await compressor.compress(messages)

    assert compressed == messages


async def test_compress_empty_messages() -> None:
    """Empty histories should not crash."""
    compressor = ContextCompressor(llm=MagicMock())

    assert await compressor.compress([]) == []
