"""Pure, immutable projections of coding-session history."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

ContextLevel = Literal["normal", "budget", "snip", "compact", "high", "emergency"]

_READ_TOOLS = frozenset({"read_file", "search", "list_files"})
_DEDUP_LEVELS = frozenset({"snip", "compact", "high", "emergency"})
_OUTPUT_CAPS: dict[ContextLevel, int] = {
    "normal": 50_000,
    "budget": 30_000,
    "snip": 30_000,
    "compact": 30_000,
    "high": 15_000,
    "emergency": 15_000,
}


class ContextProjector:
    """Return a bounded view of history without mutating canonical evidence."""

    def project(
        self,
        history: list[dict[str, Any]],
        level: ContextLevel,
    ) -> list[dict[str, Any]]:
        projected = deepcopy(history)
        cap = _OUTPUT_CAPS[level]
        tool_indexes = [index for index, item in enumerate(projected) if item.get("role") == "tool"]
        protected = set(tool_indexes[-3:])
        seen_reads: set[tuple[str, str]] = set()

        for index in reversed(tool_indexes):
            item = projected[index]
            name = str(item.get("name", ""))
            args = item.get("args")
            path = str(args.get("path", "")) if isinstance(args, dict) else ""
            signature = (name, path)
            duplicate_read = name in _READ_TOOLS and signature in seen_reads

            if level in _DEDUP_LEVELS and index not in protected and duplicate_read:
                artifact_ref = str(item.get("artifact_ref", "")) or "unavailable"
                item["content"] = f"[older duplicate result removed; artifact_ref={artifact_ref}]"
            else:
                if name in _READ_TOOLS:
                    seen_reads.add(signature)
                item["content"] = _bounded_preview(
                    str(item.get("content", "")),
                    cap,
                    str(item.get("artifact_ref", "")),
                )
        return projected


def _bounded_preview(content: str, cap: int, artifact_ref: str) -> str:
    if len(content) <= cap:
        return content
    reference = artifact_ref or "unavailable"
    marker = f"\n...[tool output truncated; artifact_ref={reference}]...\n"
    available = cap - len(marker)
    if available <= 0:
        return marker[:cap]
    head = (available + 1) // 2
    tail = available - head
    return marker.join((content[:head], content[-tail:] if tail else ""))
