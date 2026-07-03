"""Lightweight passphrase authentication for local demos."""

import hashlib
import hmac


class AuthManager:
    """口令验证 — 轻量级多用户隔离。

    不做注册/登录/JWT，仅验证口令并返回稳定的 opaque user_id。
    未配置口令时允许匿名访问，方便本地开发。
    """

    def __init__(self, access_codes: str) -> None:
        """Create an auth manager from comma-separated access codes."""
        self._codes = tuple(code.strip() for code in access_codes.split(",") if code.strip())

    def verify(self, passphrase: str) -> str | None:
        """验证口令，返回 user_id；无效时返回 None。"""
        if not self._codes:
            return "anonymous"
        for code in self._codes:
            if hmac.compare_digest(passphrase, code):
                return self._passphrase_to_user_id(passphrase)
        return None

    @staticmethod
    def _passphrase_to_user_id(passphrase: str) -> str:
        """口令转 user_id，不暴露原始口令。"""
        digest = hashlib.sha256(passphrase.encode("utf-8")).hexdigest()
        return f"u_{digest[:16]}"
