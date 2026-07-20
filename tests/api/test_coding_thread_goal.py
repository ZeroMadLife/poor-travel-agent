from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from tests.api.test_coding_routes import FakeModel


def _app(tmp_path: Path):
    return create_app(
        coding_model_factory=FakeModel,
        coding_workspace_root=tmp_path,
        coding_storage_root=tmp_path / ".coding",
        coding_default_runtime_profile="legacy",
    )


def _receive_until_terminal(websocket) -> list[dict]:
    events: list[dict] = []
    while True:
        event = websocket.receive_json()
        events.append(event)
        if event["kind"] == "terminal":
            return events


def test_thread_goal_crud_evaluate_continue_and_timeline_audit(tmp_path: Path) -> None:
    app = _app(tmp_path)
    with TestClient(app) as client:
        session_id = client.post("/api/v1/coding/session", json={}).json()["session_id"]
        assert client.get(f"/api/v1/coding/{session_id}/goal").json() == {
            "goal": None,
            "revision": 0,
        }

        created = client.put(
            f"/api/v1/coding/{session_id}/goal",
            json={
                "expected_revision": 0,
                "description": "解释 checkpoint 恢复边界",
                "completion_criteria": ["引用官方资料", "比较 thread 与 checkpoint"],
            },
        )
        assert created.status_code == 200
        goal = created.json()["goal"]
        assert goal["revision"] == 1
        assert goal["evaluation"]["blocker"] == "goal_not_met_yet"

        stale = client.put(
            f"/api/v1/coding/{session_id}/goal",
            json={
                "expected_revision": 0,
                "description": "stale",
                "completion_criteria": ["stale"],
            },
        )
        assert stale.status_code == 409
        assert stale.json()["detail"]["current_revision"] == 1

        prepared = client.post(
            f"/api/v1/coding/{session_id}/goal/continue",
            json={"expected_revision": 1},
        )
        assert prepared.status_code == 200
        assert prepared.json()["goal_revision"] == 1
        assert "checkpoint 恢复边界" in prepared.json()["prompt"]

        with client.websocket_connect(f"/api/v1/coding/{session_id}/stream") as websocket:
            websocket.send_json(
                {
                    "content": prepared.json()["prompt"],
                    "thread_goal_revision": 1,
                }
            )
            events = _receive_until_terminal(websocket)

        started = next(item for item in events if item["payload"].get("event") == "run_started")
        assert started["payload"]["thread_goal"]["revision"] == 1
        assert started["payload"]["thread_goal"]["goal_id"] == goal["goal_id"]

        evaluated = client.post(
            f"/api/v1/coding/{session_id}/goal/evaluate",
            json={"expected_revision": 1},
        )
        assert evaluated.status_code == 200
        assert evaluated.json()["goal"]["revision"] == 2
        assert evaluated.json()["goal"]["evaluation"]["source_run_id"] == started["run_id"]

        timeline = client.get(f"/api/v1/coding/session/{session_id}/timeline?limit=100").json()[
            "items"
        ]
        lifecycle = [
            item["payload"]["type"]
            for item in timeline
            if item["payload"].get("type", "").startswith("thread_goal_")
        ]
        assert lifecycle == ["thread_goal_updated", "thread_goal_evaluated"]

        cleared = client.post(
            f"/api/v1/coding/{session_id}/goal/clear",
            json={"expected_revision": 2},
        )
        assert cleared.status_code == 204
        assert client.get(f"/api/v1/coding/{session_id}/goal").json() == {
            "goal": None,
            "revision": 3,
        }

        recreated = client.put(
            f"/api/v1/coding/{session_id}/goal",
            json={
                "expected_revision": 3,
                "description": "重建后的新目标",
                "completion_criteria": ["revision 继续单调增长"],
            },
        )
        assert recreated.status_code == 200
        assert recreated.json()["goal"]["revision"] == 4


def test_stale_continue_revision_is_rejected_before_model_execution(tmp_path: Path) -> None:
    app = _app(tmp_path)
    with TestClient(app) as client:
        session_id = client.post("/api/v1/coding/session", json={}).json()["session_id"]
        client.put(
            f"/api/v1/coding/{session_id}/goal",
            json={
                "expected_revision": 0,
                "description": "first",
                "completion_criteria": ["one"],
            },
        )
        client.put(
            f"/api/v1/coding/{session_id}/goal",
            json={
                "expected_revision": 1,
                "description": "second",
                "completion_criteria": ["two"],
            },
        )

        with client.websocket_connect(f"/api/v1/coding/{session_id}/stream") as websocket:
            websocket.send_json({"content": "continue stale", "thread_goal_revision": 1})
            events = _receive_until_terminal(websocket)

    error = next(item for item in events if item["payload"].get("type") == "error")
    assert "revision changed" in error["payload"]["message"]
    assert events[-1]["payload"] == {"event": "input_rejected"}
