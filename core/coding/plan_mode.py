"""Plan mode state for coding sessions."""

from __future__ import annotations

import re
from pathlib import Path


class PlanModeManager:
    """Track the active runtime mode and plan artifact path."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self.mode = "default"
        self.topic = ""
        self.plan_path = ""

    def enter(self, topic: str, path: str | None = None) -> str:
        """Enter plan mode and return the workspace-relative plan path."""
        plan_path = self._plan_path(topic, path)
        self.mode = "plan"
        self.topic = topic
        self.plan_path = plan_path
        (self.workspace_root / plan_path).parent.mkdir(parents=True, exist_ok=True)
        return plan_path

    def exit(self) -> None:
        """Exit plan mode."""
        self.mode = "default"
        self.topic = ""
        self.plan_path = ""

    def to_dict(self) -> dict[str, str]:
        """Return JSON-serializable state."""
        return {"mode": self.mode, "topic": self.topic, "plan_path": self.plan_path}

    @staticmethod
    def _plan_path(topic: str, path: str | None = None) -> str:
        if path:
            value = path.strip()
            if value.startswith("./"):
                value = value[2:]
        else:
            value = f".coding/plans/{_slug(topic)}-plan.md"
        if (
            not value.startswith(".coding/plans/")
            or value.endswith("/")
            or ".." in value.split("/")
        ):
            raise ValueError("plan path must stay under .coding/plans/")
        return value


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "plan"
