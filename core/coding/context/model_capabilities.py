"""Server-owned model context-window configuration."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any, cast

from core.coding.context.budget import ContextPolicy

_ENV_NAME = "SAGE_MODEL_CONTEXT_WINDOWS"


class ModelCapabilityRegistry:
    """Resolve explicit model capabilities without guessing vendor limits."""

    def __init__(self, capabilities: Mapping[str, object] | None = None) -> None:
        self._policies: dict[str, ContextPolicy] = {}
        for model_id, value in (capabilities or {}).items():
            if not isinstance(model_id, str) or not model_id.strip():
                raise ValueError("model identifiers must be non-empty strings")
            self._policies[model_id] = self._coerce_policy(value)

    @classmethod
    def from_env(cls, value: str | None = None) -> ModelCapabilityRegistry:
        raw = os.getenv(_ENV_NAME, "") if value is None else value
        if not raw.strip():
            return cls()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{_ENV_NAME} must be valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"{_ENV_NAME} must be a JSON object")
        return cls(parsed)

    @classmethod
    def from_model(cls, model: object) -> ContextPolicy | None:
        window = getattr(model, "context_window_tokens", None)
        reserve = getattr(model, "output_reserve_tokens", None)
        if window is None and reserve is None:
            return None
        if not _strict_positive_int(window) or not _strict_positive_int(reserve):
            raise ValueError("model context attributes must be positive integers")
        return ContextPolicy(
            context_window_tokens=cast(int, window),
            output_reserve_tokens=cast(int, reserve),
        )

    def resolve(self, model_spec: object) -> ContextPolicy | None:
        if isinstance(model_spec, str):
            return self._policies.get(model_spec)
        explicit = self.from_model(model_spec)
        if explicit is not None:
            return explicit
        for attribute in ("model", "model_id", "model_name"):
            model_id = getattr(model_spec, attribute, None)
            if isinstance(model_id, str) and model_id in self._policies:
                return self._policies[model_id]
        return None

    @staticmethod
    def _coerce_policy(value: object) -> ContextPolicy:
        if _strict_positive_int(value):
            return ContextPolicy(context_window_tokens=cast(int, value))
        if not isinstance(value, Mapping):
            raise ValueError("model capability must be an integer or object")
        allowed = {"context_window_tokens", "output_reserve_tokens"}
        if set(value) - allowed or "context_window_tokens" not in value:
            raise ValueError("model capability has unknown or missing fields")
        window = value["context_window_tokens"]
        reserve = value.get("output_reserve_tokens", 20_000)
        if not _strict_positive_int(window) or not _strict_positive_int(reserve):
            raise ValueError("model capability values must be positive integers")
        return ContextPolicy(
            context_window_tokens=cast(int, window),
            output_reserve_tokens=cast(int, reserve),
        )


def _strict_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0
