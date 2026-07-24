#!/usr/bin/env python3
"""Bounded root-owned controller for public knowledge package revisions."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TextIO


def _add_application_root() -> None:
    repository_root = Path(__file__).resolve().parent.parent
    if not (repository_root / "public_agent").is_dir():
        repository_root = Path(os.getenv("SAGE_PUBLIC_APP_ROOT", "/opt/sage/app"))
    sys.path.insert(0, str(repository_root))


_add_application_root()

from public_agent.registry import (  # noqa: E402
    PublishedPackageError,
    PublishedPackageRegistry,
)

DEFAULT_REGISTRY_ROOT = Path("/var/lib/sage-public-release/packages")
_MAX_REQUEST_BYTES = 2 * 1024 * 1024


def parse_request(stream: TextIO) -> dict[str, Any]:
    raw = stream.read(_MAX_REQUEST_BYTES + 1)
    if len(raw.encode("utf-8")) > _MAX_REQUEST_BYTES:
        raise PublishedPackageError("公开资料包操作请求超过 2 MiB")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PublishedPackageError("公开资料包操作请求不是有效 JSON") from exc
    if not isinstance(payload, dict):
        raise PublishedPackageError("公开资料包操作请求必须是 JSON object")
    action = payload.get("action")
    allowed = {
        "status": {"action"},
        "stage": {"action", "package"},
        "publish": {"action", "package_id", "revision", "expected_active_revision"},
        "revoke": {
            "action",
            "package_id",
            "revision",
            "expected_active_revision",
            "reason",
        },
    }
    if not isinstance(action, str) or action not in allowed or set(payload) != allowed[action]:
        raise PublishedPackageError("公开资料包操作 action 或字段无效")
    if action == "stage" and not isinstance(payload.get("package"), dict):
        raise PublishedPackageError("stage.package 必须是 JSON object")
    if action in {"publish", "revoke"} and (
        not isinstance(payload.get("package_id"), str)
        or not isinstance(payload.get("revision"), str)
    ):
        raise PublishedPackageError("package_id 和 revision 必须是 string")
    expected = payload.get("expected_active_revision")
    if action in {"publish", "revoke"} and expected is not None and not isinstance(expected, str):
        raise PublishedPackageError("expected_active_revision 必须是 string 或 null")
    if action == "revoke" and not isinstance(payload.get("reason"), str):
        raise PublishedPackageError("revoke.reason 必须是 string")
    return payload


def execute(
    registry: PublishedPackageRegistry,
    request: Mapping[str, Any],
    *,
    actor: str,
) -> dict[str, Any]:
    action = str(request["action"])
    if action == "status":
        return registry.status()
    if action == "stage":
        package = request["package"]
        if not isinstance(package, dict):
            raise PublishedPackageError("stage.package 必须是 JSON object")
        return registry.stage_payload(package, actor=actor)
    package_id = str(request["package_id"])
    revision = str(request["revision"])
    expected = request.get("expected_active_revision")
    expected_revision = str(expected) if expected is not None else None
    if action == "publish":
        return registry.activate(
            package_id,
            revision,
            expected_active_revision=expected_revision,
            actor=actor,
        )
    if action == "revoke":
        return registry.revoke(
            package_id,
            revision,
            expected_active_revision=expected_revision,
            actor=actor,
            reason=str(request["reason"]),
        )
    raise PublishedPackageError("公开资料包操作无效")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry-root", type=Path, default=DEFAULT_REGISTRY_ROOT)
    parser.add_argument("--bootstrap-package", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    registry = PublishedPackageRegistry(args.registry_root.resolve())
    actor = os.getenv("SUDO_USER") or os.getenv("USER") or "root"
    try:
        if args.bootstrap_package is not None:
            result = registry.bootstrap(args.bootstrap_package.resolve(), actor=actor)
        else:
            result = execute(registry, parse_request(sys.stdin), actor=actor)
    except PublishedPackageError as exc:
        print(f"public-packagectl blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
