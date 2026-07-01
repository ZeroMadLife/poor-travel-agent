"""Pytest global fixtures."""

from collections.abc import Iterator

import pytest
from _pytest.monkeypatch import MonkeyPatch


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch: MonkeyPatch) -> Iterator[None]:
    """Inject test environment variables for all tests."""
    test_env = {
        "AMAP_API_KEY": "test-amap-key",
        "QWEATHER_API_KEY": "test-weather-key",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": "6333",
        "LLM_MODEL": "gpt-4o-mini",
        "APP_ENV": "test",
    }
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    yield
