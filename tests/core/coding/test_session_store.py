"""Coding session store tests."""

from pathlib import Path

from core.coding.session_store import CodingSessionStore


def test_session_store_lists_session_summaries(tmp_path: Path) -> None:
    """Session store exposes Hermes-style session summaries for the workbench."""
    store = CodingSessionStore(tmp_path)
    store.save(
        {
            "id": "s-old",
            "workspace_root": "/tmp/old",
            "created_at": "2026-07-08T09:00:00",
            "updated_at": "2026-07-08T09:10:00",
            "runtime_mode": {"mode": "default"},
            "history": [{"role": "user", "content": "读 README"}],
        }
    )
    store.save(
        {
            "id": "s-new",
            "workspace_root": "/tmp/new",
            "created_at": "2026-07-08T10:00:00",
            "updated_at": "2026-07-08T10:20:00",
            "runtime_mode": {"mode": "plan"},
            "history": [],
        }
    )

    summaries = store.list_sessions()

    assert summaries == [
        {
            "session_id": "s-new",
            "title": "new",
            "workspace_root": "/tmp/new",
            "created_at": "2026-07-08T10:00:00",
            "updated_at": "2026-07-08T10:20:00",
            "runtime_mode": "plan",
            "message_count": 0,
        },
        {
            "session_id": "s-old",
            "title": "读 README",
            "workspace_root": "/tmp/old",
            "created_at": "2026-07-08T09:00:00",
            "updated_at": "2026-07-08T09:10:00",
            "runtime_mode": "default",
            "message_count": 1,
        },
    ]
