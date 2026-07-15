"""V7.2 durable batch ingestion REST and WebSocket contracts."""

from __future__ import annotations

import asyncio
import subprocess
import time
from pathlib import Path
from typing import Any

import fakeredis.aioredis
from fastapi.testclient import TestClient

from api.main import create_app
from core.knowledge import KnowledgeSourceRoot, KnowledgeStore
from core.knowledge.jobs import (
    KnowledgeJobRepository,
    KnowledgeJobService,
    RedisKnowledgeJobQueue,
)
from db.database import create_engine, create_session_factory
from db.migrations import init_db


def _app(tmp_path: Path) -> tuple[Any, Path, Any, Any]:
    coding = tmp_path / "coding"
    coding.mkdir()
    vault = tmp_path / "vault"
    vault.mkdir()
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=knowledge,
        check=True,
        capture_output=True,
        text=True,
    )
    source_roots = {
        "vault": KnowledgeSourceRoot(root_id="vault", kind="obsidian", label="Vault", path=vault)
    }
    store = KnowledgeStore(knowledge, knowledge / ".sage" / "knowledge.sqlite3", source_roots)
    store.initialize()
    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'jobs.sqlite3'}")
    asyncio.run(init_db(engine))
    redis = fakeredis.aioredis.FakeRedis()
    service = KnowledgeJobService(
        store,
        KnowledgeJobRepository(create_session_factory(engine)),
        RedisKnowledgeJobQueue(redis, stream=f"api-test:{tmp_path.name}"),
        poll_seconds=0.01,
        retry_base_seconds=0,
    )
    app = create_app(
        coding_workspace_root=coding,
        coding_storage_root=tmp_path / ".coding",
        cloud_app_env="development",
        knowledge_workspace_root=knowledge,
        knowledge_source_roots=source_roots,
        knowledge_job_service=service,
    )
    return app, vault, engine, redis


def _wait_for_terminal(client: TestClient, job_id: str) -> dict[str, Any]:
    for _ in range(200):
        payload: dict[str, Any] = client.get(f"/api/v1/knowledge/jobs/{job_id}").json()
        if payload["status"] in {"completed", "completed_with_errors", "cancelled"}:
            return payload
        time.sleep(0.01)
    raise AssertionError("knowledge job did not finish")


def test_batch_job_progress_rest_and_websocket_replay(tmp_path: Path) -> None:
    app, vault, engine, redis = _app(tmp_path)
    (vault / "one.md").write_text("# One\n", encoding="utf-8")
    (vault / "nested").mkdir()
    (vault / "nested" / "two.md").write_text("# Two\n", encoding="utf-8")

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/knowledge/jobs",
            json={"source_root_id": "vault", "relative_directory": "."},
        )
        assert created.status_code == 201
        job_id = created.json()["job_id"]
        completed = _wait_for_terminal(client, job_id)
        assert completed["total_items"] == 2
        assert completed["succeeded_items"] == 2
        assert str(vault) not in created.text
        compact = client.get(
            f"/api/v1/knowledge/jobs/{job_id}",
            params={"include_items": "false"},
        ).json()
        assert compact["items"] == []
        listed = client.get("/api/v1/knowledge/jobs").json()["jobs"][0]
        assert listed["items"] == []

        first_page = client.get(
            f"/api/v1/knowledge/jobs/{job_id}/events", params={"limit": 2}
        ).json()
        assert len(first_page["items"]) == 2
        assert first_page["has_more"] is True
        second_page = client.get(
            f"/api/v1/knowledge/jobs/{job_id}/events",
            params={"after": first_page["next_cursor"]},
        ).json()
        assert second_page["items"][0]["sequence"] > first_page["next_cursor"]

        with client.websocket_connect(
            f"/api/v1/knowledge/jobs/{job_id}/stream?after=0"
        ) as websocket:
            first_event = websocket.receive_json()
        assert first_event["sequence"] == 1
        assert str(vault) not in str(first_event)

    asyncio.run(redis.aclose())
    asyncio.run(engine.dispose())


def test_batch_job_cancel_and_validation_contracts(tmp_path: Path) -> None:
    app, vault, engine, redis = _app(tmp_path)
    (vault / "one.md").write_text("# One\n", encoding="utf-8")

    client = TestClient(app)
    traversal = client.post(
        "/api/v1/knowledge/jobs",
        json={"source_root_id": "vault", "relative_directory": "../outside"},
    )
    assert traversal.status_code == 400
    missing = client.get("/api/v1/knowledge/jobs/missing")
    assert missing.status_code == 404

    created = client.post(
        "/api/v1/knowledge/jobs",
        json={"source_root_id": "vault", "relative_directory": "."},
    ).json()
    cancelled = client.post(f"/api/v1/knowledge/jobs/{created['job_id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["cancelled_items"] == 1

    asyncio.run(redis.aclose())
    asyncio.run(engine.dispose())
