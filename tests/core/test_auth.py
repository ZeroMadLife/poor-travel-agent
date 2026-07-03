"""Passphrase auth tests."""

from core.auth import AuthManager


def test_verify_valid_passphrase_returns_user_id() -> None:
    """Valid passphrases should map to stable opaque user IDs."""
    manager = AuthManager("tour2026,friend01")

    user_id = manager.verify("tour2026")

    assert user_id is not None
    assert user_id.startswith("u_")
    assert "tour2026" not in user_id
    assert manager.verify("tour2026") == user_id


def test_verify_invalid_passphrase_returns_none() -> None:
    """Invalid passphrases should not authenticate."""
    manager = AuthManager("tour2026")

    assert manager.verify("wrong") is None


def test_verify_different_passphrases_have_different_user_ids() -> None:
    """Each passphrase gets an isolated user scope."""
    manager = AuthManager("tour2026,friend01")

    assert manager.verify("tour2026") != manager.verify("friend01")


def test_verify_empty_codes_allows_anonymous() -> None:
    """Development mode without configured codes should allow anonymous access."""
    manager = AuthManager("")

    assert manager.verify("anything") == "anonymous"
