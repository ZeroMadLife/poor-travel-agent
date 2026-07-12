"""Strict model adapter for structured context summaries."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Mapping
from typing import Any

from core.coding.context.summary import CompactionSummary

_FENCE = re.compile(r"\A```(?:json)?\s*\n?(.*?)\n?```\s*\Z", re.DOTALL | re.IGNORECASE)
_INSTRUCTION = "Return exactly one JSON object matching the compaction summary schema."


class StructuredSummarizer:
    """Call one model with a canonical request and accept JSON only."""

    def __init__(self, model: object, *, timeout_seconds: float = 30.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def summarize(
        self,
        *,
        archived_history: list[dict[str, Any]],
        previous_summary: CompactionSummary | None,
        focus: str,
        max_tokens: int,
        source_transcript_range: tuple[int, int],
        repair_feedback: str | None,
    ) -> Mapping[str, Any]:
        request = {
            "archived": archived_history,
            "focus": focus,
            "max_tokens": max_tokens,
            "previous": (
                previous_summary.model_dump(mode="json") if previous_summary is not None else None
            ),
            "range": list(source_transcript_range),
            "repair": repair_feedback,
        }
        payload = json.dumps(
            request,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        try:
            raw = await asyncio.wait_for(
                self._invoke(f"{_INSTRUCTION}\n{payload}"),
                timeout=self.timeout_seconds,
            )
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            raise TimeoutError("structured summarization timed out") from None
        except Exception:
            raise RuntimeError("structured summarization failed") from None
        return _parse_single_object(raw)

    async def _invoke(self, prompt: str) -> str:
        complete = getattr(self.model, "complete", None)
        ainvoke = getattr(self.model, "ainvoke", None)
        if callable(complete):
            response = await complete(prompt)
        elif callable(ainvoke):
            response = await ainvoke(prompt)
        else:
            raise TypeError("model has no supported async completion method")
        content = getattr(response, "content", response)
        if not isinstance(content, str):
            raise TypeError("model response content must be text")
        return content


def _parse_single_object(raw: str) -> Mapping[str, Any]:
    candidate = raw.strip()
    match = _FENCE.fullmatch(candidate)
    if match is not None:
        candidate = match.group(1).strip()
    decoder = json.JSONDecoder()
    try:
        value, end = decoder.raw_decode(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError("summary must contain exactly one JSON object") from exc
    if candidate[end:].strip() or not isinstance(value, dict):
        raise ValueError("summary must contain exactly one JSON object")
    return value
