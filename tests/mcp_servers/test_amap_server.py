"""Amap MCP Server tests."""

from typing import Any

from mcp_servers.amap.server import create_amap_server


def _tools(server: Any) -> dict[str, Any]:
    return server._tool_manager._tools


def test_server_exposes_search_attractions_tool() -> None:
    """Server exposes the search_attractions tool."""
    server = create_amap_server(api_key="test-key")
    assert "search_attractions" in _tools(server)


def test_server_exposes_get_route_tool() -> None:
    """Server exposes the get_route tool."""
    server = create_amap_server(api_key="test-key")
    assert "get_route" in _tools(server)


def test_server_exposes_geocode_tool() -> None:
    """Server exposes the geocode tool."""
    server = create_amap_server(api_key="test-key")
    assert "geocode" in _tools(server)


def test_search_attractions_tool_has_correct_schema() -> None:
    """search_attractions has the expected name and useful description."""
    server = create_amap_server(api_key="test-key")
    tool = _tools(server)["search_attractions"]
    assert tool.name == "search_attractions"
    assert "城市" in tool.description or "景点" in tool.description
