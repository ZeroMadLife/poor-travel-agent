"""Concurrent-safe daily token admission budget for the public Agent."""

from __future__ import annotations

import fcntl
import json
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from threading import Lock
from typing import TypedDict


class PublicBudgetExceeded(RuntimeError):
    """The public model budget cannot admit another bounded request."""


@dataclass(frozen=True, slots=True)
class TokenReservation:
    day: date
    tokens: int


class _BudgetState(TypedDict):
    day: str
    used: int
    reserved: int


class DailyTokenBudget:
    def __init__(
        self,
        *,
        token_limit: int,
        reservation_tokens: int,
        today: Callable[[], date] | None = None,
        state_path: str | Path | None = None,
    ) -> None:
        if token_limit < 1 or reservation_tokens < 1:
            raise ValueError("token budget values must be positive")
        if reservation_tokens > token_limit:
            raise ValueError("request reservation cannot exceed the daily token limit")
        self.token_limit = token_limit
        self.reservation_tokens = reservation_tokens
        self._today = today or (lambda: datetime.now(UTC).date())
        self._day = self._today()
        self._used = 0
        self._reserved = 0
        self._lock = Lock()
        self._state_path = Path(state_path) if state_path else None
        if self._state_path is not None:
            self._initialize_state_file()

    def reserve(self) -> TokenReservation:
        with self._lock, self._state() as state:
            if state["used"] + state["reserved"] + self.reservation_tokens > self.token_limit:
                raise PublicBudgetExceeded("public Agent daily token budget exceeded")
            state["reserved"] += self.reservation_tokens
            return TokenReservation(date.fromisoformat(state["day"]), self.reservation_tokens)

    def commit(self, reservation: TokenReservation, actual_tokens: int) -> None:
        with self._lock, self._state() as state:
            if reservation.day.isoformat() == state["day"]:
                state["reserved"] = max(0, state["reserved"] - reservation.tokens)
                state["used"] += max(0, actual_tokens)

    def release(self, reservation: TokenReservation) -> None:
        with self._lock, self._state() as state:
            if reservation.day.isoformat() == state["day"]:
                state["reserved"] = max(0, state["reserved"] - reservation.tokens)

    @property
    def remaining(self) -> int:
        with self._lock, self._state() as state:
            return max(0, self.token_limit - state["used"] - state["reserved"])

    def _initialize_state_file(self) -> None:
        assert self._state_path is not None
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self._state_path, os.O_RDWR | os.O_CREAT, 0o600)
        os.close(descriptor)
        os.chmod(self._state_path, 0o600)
        with self._state():
            pass

    @contextmanager
    def _state(self) -> Iterator[_BudgetState]:
        if self._state_path is None:
            self._reset_if_needed()
            state: _BudgetState = {
                "day": self._day.isoformat(),
                "used": self._used,
                "reserved": self._reserved,
            }
            yield state
            self._day = date.fromisoformat(state["day"])
            self._used = state["used"]
            self._reserved = state["reserved"]
            return

        descriptor = os.open(self._state_path, os.O_RDWR)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            raw = os.read(descriptor, 4096)
            state = self._decode_state(raw)
            current = self._today().isoformat()
            if state["day"] != current:
                state = {"day": current, "used": 0, "reserved": 0}
            yield state
            encoded = (json.dumps(state, separators=(",", ":")) + "\n").encode("utf-8")
            os.lseek(descriptor, 0, os.SEEK_SET)
            os.ftruncate(descriptor, 0)
            os.write(descriptor, encoded)
            os.fsync(descriptor)
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def _decode_state(self, raw: bytes) -> _BudgetState:
        if not raw.strip():
            return {"day": self._today().isoformat(), "used": 0, "reserved": 0}
        try:
            value = json.loads(raw)
            parsed_day = date.fromisoformat(value["day"])
            used = int(value["used"])
            reserved = int(value["reserved"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("public Agent token budget state is invalid") from exc
        if used < 0 or reserved < 0:
            raise RuntimeError("public Agent token budget state is invalid")
        return {"day": parsed_day.isoformat(), "used": used, "reserved": reserved}

    def _reset_if_needed(self) -> None:
        current = self._today()
        if current != self._day:
            self._day = current
            self._used = 0
            self._reserved = 0
