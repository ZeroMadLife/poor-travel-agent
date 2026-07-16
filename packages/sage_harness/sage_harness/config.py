"""Pure configuration values for constructing a Sage harness agent."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class HarnessConfig:
    """Process-independent safety limits for one agent graph."""

    max_model_calls: int = 24
    max_run_tokens: int = 100_000

    def __post_init__(self) -> None:
        if self.max_model_calls < 1:
            raise ValueError("max_model_calls must be positive")
        if self.max_run_tokens < 1:
            raise ValueError("max_run_tokens must be positive")


@dataclass(frozen=True, slots=True)
class HarnessRunContext:
    """Server-owned identity and workspace binding for one graph invocation."""

    thread_id: str
    run_id: str
    workspace_id: str
    workspace_path: str
    surface: str = "coding"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("thread_id", "run_id", "workspace_id", "workspace_path", "surface"):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} must not be empty")


__all__ = ["HarnessConfig", "HarnessRunContext"]
