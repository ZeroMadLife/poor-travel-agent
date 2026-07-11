from __future__ import annotations

import pytest

from core.coding.persistence.transcript_store import TranscriptItem, TranscriptStore


def test_transcript_append_is_idempotent(tmp_path):
    store = TranscriptStore(tmp_path, "s1")
    item = TranscriptItem(message_id="m1", role="user", content="hello")

    assert store.append(item) is True
    assert store.append(item) is False

    assert [entry.message_id for entry in store.read_all()] == ["m1"]


def test_transcript_rebuild_preserves_idempotency(tmp_path):
    item = TranscriptItem(message_id="m1", role="assistant", content="answer")
    assert TranscriptStore(tmp_path, "s1").append(item) is True

    rebuilt = TranscriptStore(tmp_path, "s1")

    assert rebuilt.append(item) is False
    assert rebuilt.read_all() == [item]


def test_transcript_round_trips_unicode_and_metadata(tmp_path):
    item = TranscriptItem(
        message_id="m1",
        role="tool",
        content="你好，世界 🌍",
        run_id="run_1",
        turn_id="turn_1",
        call_id="call_1",
        artifact_ref="artifact.txt",
        created_at="2026-07-11T12:00:00Z",
    )
    store = TranscriptStore(tmp_path, "session")

    assert store.append(item) is True

    assert store.read_all() == [item]
    assert "你好，世界 🌍" in store.path.read_text(encoding="utf-8")


@pytest.mark.parametrize("session_id", ["", ".", "..", "nested/session", r"nested\session"])
def test_transcript_rejects_invalid_session_ids(tmp_path, session_id):
    with pytest.raises(ValueError):
        TranscriptStore(tmp_path, session_id)
