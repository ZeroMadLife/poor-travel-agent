"""Weather MCP Server tests."""

from typing import Any

from mcp_servers.weather.server import create_weather_server


def _tools(server: Any) -> dict[str, Any]:
    return server._tool_manager._tools


def test_server_exposes_get_weather_tool() -> None:
    """Server exposes get_weather."""
    server = create_weather_server(api_key="test-key")
    assert "get_weather" in _tools(server)


def test_server_exposes_get_forecast_tool() -> None:
    """Server exposes get_forecast."""
    server = create_weather_server(api_key="test-key")
    assert "get_forecast" in _tools(server)


def test_server_exposes_get_weather_alert_tool() -> None:
    """Server exposes get_weather_alert."""
    server = create_weather_server(api_key="test-key")
    assert "get_weather_alert" in _tools(server)


def test_get_weather_tool_description_mentions_planning() -> None:
    """The weather tool description mentions weather context."""
    server = create_weather_server(api_key="test-key")
    tool = _tools(server)["get_weather"]
    assert "天气" in tool.description
