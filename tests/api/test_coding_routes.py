"""Coding API route tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app


class FakeModel:
    """Deterministic model for coding route tests."""

    def __init__(self) -> None:
        self.responses = [
            '<tool>{"name":"read_file","args":{"path":"README.md"}}</tool>',
            "<final>README 里能看到项目内容。</final>",
        ]

    async def complete(self, prompt: str) -> str:
        _ = prompt
        return self.responses.pop(0)


def test_create_coding_session(tmp_path: Path) -> None:
    """POST /api/v1/coding/session creates a coding runtime session."""
    client = TestClient(
        create_app(
            coding_model_factory=FakeModel,
            coding_workspace_root=tmp_path,
            coding_storage_root=tmp_path / ".coding",
        )
    )

    response = client.post("/api/v1/coding/session", json={})

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"]
    assert data["workspace_root"] == str(tmp_path.resolve())


def test_create_coding_session_rejects_workspace_outside_configured_root(
    tmp_path: Path,
) -> None:
    """Workspace overrides must stay within the configured coding root."""
    outside_root = tmp_path.parent / f"{tmp_path.name}-outside"
    outside_root.mkdir()
    client = TestClient(
        create_app(
            coding_model_factory=FakeModel,
            coding_workspace_root=tmp_path,
            coding_storage_root=tmp_path / ".coding",
        )
    )

    response = client.post(
        "/api/v1/coding/session",
        json={"workspace_root": str(outside_root)},
    )

    assert response.status_code == 400
    assert "configured coding workspace" in response.json()["detail"]


def test_coding_websocket_streams_engine_events(tmp_path: Path) -> None:
    """Coding WebSocket streams tool and final events from the runtime."""
    (tmp_path / "README.md").write_text("TourSwarm API coding\n", encoding="utf-8")
    client = TestClient(
        create_app(
            coding_model_factory=FakeModel,
            coding_workspace_root=tmp_path,
            coding_storage_root=tmp_path / ".coding",
        )
    )
    session_id = client.post("/api/v1/coding/session", json={}).json()["session_id"]

    with client.websocket_connect(f"/api/v1/coding/{session_id}/stream") as websocket:
        websocket.send_json({"content": "读 README.md"})
        events = [websocket.receive_json() for _ in range(7)]

    assert [event["type"] for event in events] == [
        "model_requested",
        "model_parsed",
        "tool_call",
        "tool_result",
        "model_requested",
        "model_parsed",
        "final",
    ]
    assert events[2]["tool"] == "read_file"
    assert "TourSwarm API coding" in events[3]["content"]
    assert events[-1]["content"] == "README 里能看到项目内容。"
