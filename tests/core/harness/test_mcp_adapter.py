"""MCP catalog boundary tests for the DeerFlow-compatible runtime."""

from __future__ import annotations

import asyncio

from langchain_core.tools import StructuredTool

from core.config.settings import Settings
from core.harness.mcp_adapter import (
    build_configured_mcp_catalog,
    build_configured_mcp_manager,
    mcp_catalog_event,
)


def test_mcp_catalog_exposes_status_without_connection_secrets() -> None:
    settings = Settings(
        amap_api_key="secret-amap",
        qweather_api_key="secret-weather",
        qweather_base_url="https://weather.test/v7",
        qweather_geo_url="https://geo.test/geoapi/v2",
    )
    catalog = build_configured_mcp_catalog(settings)

    servers = asyncio.run(catalog.list_servers())
    rendered = repr(servers)

    assert {server.name for server in servers} == {"amap", "weather", "scenic"}
    assert all(server.status == "configured" for server in servers)
    assert "secret-amap" not in rendered
    assert "secret-weather" not in rendered
    assert "command" not in rendered
    assert "env" not in rendered


def test_mcp_catalog_marks_missing_credentials_without_connecting() -> None:
    catalog = build_configured_mcp_catalog(Settings(amap_api_key="", qweather_api_key=""))

    servers = {server.name: server for server in asyncio.run(catalog.list_servers())}

    assert servers["amap"].status == "unconfigured"
    assert servers["weather"].status == "unconfigured"
    assert servers["scenic"].status == "configured"


def test_mcp_catalog_event_contains_only_sanitized_metadata() -> None:
    catalog = build_configured_mcp_catalog(
        Settings(amap_api_key="secret-amap", qweather_api_key="secret-weather")
    )

    event = asyncio.run(mcp_catalog_event(catalog, session_id="s1", run_id="r1"))

    assert event.payload["type"] == "mcp_catalog_updated"
    assert event.event_id == "harness:r1:mcp-catalog"
    rendered = repr(event.payload)
    assert "secret-amap" not in rendered
    assert "secret-weather" not in rendered
    assert "command" not in rendered
    assert "args" not in rendered
    assert "env" not in rendered


def test_live_mcp_manager_discovers_prefixed_tools_without_public_secrets() -> None:
    class FakeClient:
        async def get_tools(self, *, server_name: str):
            assert server_name == "scenic"
            return [
                StructuredTool.from_function(
                    coroutine=lambda query: query,
                    name="scenic_search",
                    description="Search scenic records",
                )
            ]

    settings = Settings(amap_api_key="private-amap", qweather_api_key="private-weather")
    manager = build_configured_mcp_manager(
        settings,
        scenic_data_path="data/mock/scenic_spots.json",
        client_factory=lambda connections: FakeClient(),
    )

    async def run():
        from sage_harness import McpScope

        return await manager.load_tools(McpScope("owner", "workspace", "thread"))

    snapshot = asyncio.run(run())

    assert [tool.name for tool in snapshot.tools] == ["scenic_search"]
    statuses = {server.name: server.status for server in snapshot.catalog.servers}
    assert statuses["scenic"] == "connected"
    assert "private-amap" not in repr(snapshot)
    assert "private-weather" not in repr(snapshot)
