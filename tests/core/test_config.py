"""Configuration module tests."""

from core.config.settings import Settings


def test_settings_loads_from_env() -> None:
    """Settings load API keys from environment variables."""
    settings = Settings()
    assert settings.amap_api_key == "test-amap-key"
    assert settings.qweather_api_key == "test-weather-key"


def test_settings_has_amap_base_url() -> None:
    """Amap API base URL has a default value."""
    settings = Settings()
    assert "restapi.amap.com" in settings.amap_base_url


def test_settings_has_qweather_base_url() -> None:
    """QWeather API base URL has a default value."""
    settings = Settings()
    assert "api.qweather.com" in settings.qweather_base_url
