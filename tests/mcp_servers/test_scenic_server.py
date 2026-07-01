"""Scenic MCP Server tests."""

from pathlib import Path
from typing import Any

import pytest

from mcp_servers.scenic.client import ScenicClient
from mcp_servers.scenic.server import create_scenic_server

MOCK_DIR = Path(__file__).parent.parent.parent / "data" / "mock"


@pytest.fixture
def scenic_client() -> ScenicClient:
    """Return a local scenic test client."""
    return ScenicClient(data_path=str(MOCK_DIR / "scenic_spots.json"))


def _tools(server: Any) -> dict[str, Any]:
    return server._tool_manager._tools


def test_server_exposes_search_scenic_spots() -> None:
    server = create_scenic_server(data_path=str(MOCK_DIR / "scenic_spots.json"))
    assert "search_scenic_spots" in _tools(server)


def test_server_exposes_get_scenic_detail() -> None:
    server = create_scenic_server(data_path=str(MOCK_DIR / "scenic_spots.json"))
    assert "get_scenic_detail" in _tools(server)


def test_search_scenic_spots_by_city(scenic_client: ScenicClient) -> None:
    """Search scenic spots by city."""
    result = scenic_client.search_scenic_spots(city="杭州")
    assert len(result) == 3
    assert all(spot["city"] == "杭州" for spot in result)


def test_search_scenic_spots_by_category(scenic_client: ScenicClient) -> None:
    """Search scenic spots by category."""
    result = scenic_client.search_scenic_spots(city="杭州", category="自然风光")
    assert len(result) == 1
    assert result[0]["name"] == "西湖"


def test_search_scenic_spots_free_only(scenic_client: ScenicClient) -> None:
    """Filter free scenic spots."""
    result = scenic_client.search_scenic_spots(city="杭州", free_only=True)
    assert all(spot["ticket_price"] == 0 for spot in result)


def test_get_scenic_detail(scenic_client: ScenicClient) -> None:
    """Get scenic spot details."""
    result = scenic_client.get_scenic_detail("hangzhou-xihu")
    assert result is not None
    assert result["name"] == "西湖"
    assert result["ticket_price"] == 0
    assert result["recommended_duration_hours"] == 4


def test_get_scenic_detail_not_found(scenic_client: ScenicClient) -> None:
    """Unknown scenic spot IDs return None."""
    result = scenic_client.get_scenic_detail("nonexistent")
    assert result is None
