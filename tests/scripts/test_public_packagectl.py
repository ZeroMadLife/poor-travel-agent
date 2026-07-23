"""Strict stdin contract for the root-owned public package controller."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from public_agent.registry import PublishedPackageError, PublishedPackageRegistry
from scripts.public_packagectl import execute, parse_request


def test_request_contract_accepts_exact_lifecycle_actions() -> None:
    assert parse_request(io.StringIO('{"action":"status"}')) == {"action": "status"}
    publish = {
        "action": "publish",
        "package_id": "sage-public",
        "revision": "v2",
        "expected_active_revision": "v1",
    }
    assert parse_request(io.StringIO(json.dumps(publish))) == publish

    with pytest.raises(PublishedPackageError, match="字段无效"):
        parse_request(io.StringIO('{"action":"status","shell":"id"}'))
    with pytest.raises(PublishedPackageError, match="字段无效"):
        parse_request(io.StringIO('{"action":"delete","revision":"v1"}'))
    with pytest.raises(PublishedPackageError, match="必须是 string"):
        parse_request(
            io.StringIO(
                '{"action":"publish","package_id":1,"revision":"v2",'
                '"expected_active_revision":"v1"}'
            )
        )
    with pytest.raises(PublishedPackageError, match="reason 必须是 string"):
        parse_request(
            io.StringIO(
                '{"action":"revoke","package_id":"sage-public","revision":"v2",'
                '"expected_active_revision":"v2","reason":1}'
            )
        )


def test_controller_stages_payload_without_accepting_an_arbitrary_source_path(
    tmp_path: Path,
) -> None:
    payload = json.loads(Path("data/public/sage-public-v1.json").read_text(encoding="utf-8"))
    registry = PublishedPackageRegistry(tmp_path)

    result = execute(registry, {"action": "stage", "package": payload}, actor="sage-deploy")

    assert result["status"] == "staged"
    assert result["active_revision"] is None
    assert (tmp_path / "packages/sage-public/2026-07-22.1.json").is_file()
