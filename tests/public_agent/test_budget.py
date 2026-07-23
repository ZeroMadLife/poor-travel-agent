"""Daily public model budget coverage."""

from datetime import date

import pytest

from public_agent.budget import DailyTokenBudget, PublicBudgetExceeded


def test_budget_reserves_concurrent_capacity_and_releases_failures() -> None:
    current = [date(2026, 7, 22)]
    budget = DailyTokenBudget(
        token_limit=20,
        reservation_tokens=10,
        today=lambda: current[0],
    )

    first = budget.reserve()
    second = budget.reserve()
    with pytest.raises(PublicBudgetExceeded):
        budget.reserve()

    budget.release(second)
    budget.commit(first, 7)
    assert budget.remaining == 13


def test_budget_resets_on_the_next_utc_day() -> None:
    current = [date(2026, 7, 22)]
    budget = DailyTokenBudget(
        token_limit=10,
        reservation_tokens=10,
        today=lambda: current[0],
    )
    reservation = budget.reserve()
    budget.commit(reservation, 10)

    current[0] = date(2026, 7, 23)
    assert budget.remaining == 10


def test_persistent_budget_survives_process_restart(tmp_path) -> None:
    current = [date(2026, 7, 22)]
    state_path = tmp_path / "budget.json"
    first = DailyTokenBudget(
        token_limit=20,
        reservation_tokens=10,
        today=lambda: current[0],
        state_path=state_path,
    )
    reservation = first.reserve()
    first.commit(reservation, 7)

    restarted = DailyTokenBudget(
        token_limit=20,
        reservation_tokens=10,
        today=lambda: current[0],
        state_path=state_path,
    )
    assert restarted.remaining == 13

    current[0] = date(2026, 7, 23)
    assert restarted.remaining == 20


def test_persistent_budget_fails_closed_when_state_is_corrupt(tmp_path) -> None:
    state_path = tmp_path / "budget.json"
    state_path.write_text("not-json", encoding="utf-8")

    with pytest.raises(RuntimeError, match="state is invalid"):
        DailyTokenBudget(
            token_limit=20,
            reservation_tokens=10,
            state_path=state_path,
        )
