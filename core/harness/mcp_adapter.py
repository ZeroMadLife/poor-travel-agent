"""Expose the Sage MCP registry through a credential-free harness catalog."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from sage_harness import McpCatalogPort, McpConnectionStatus, McpServerReference

from core.coding.run_coordinator import RunEvent
from core.config.settings import Settings
from core.mcp_client import build_config_from_settings
from mcp_servers.registry import McpConfig


class ConfiguredMcpCatalog(McpCatalogPort):
    """Read-only view over MCP configuration; it never opens a connection."""

    def __init__(
        self,
        config: McpConfig,
        *,
        statuses: Mapping[str, McpConnectionStatus] | None = None,
    ) -> None:
        status_by_name = dict(statuses or {})
        self._servers = tuple(
            McpServerReference(
                name=name,
                transport=str(spec.get("transport", "stdio")),
                status=status_by_name.get(name, "configured"),
            )
            for name, spec in sorted(config.items())
        )

    async def list_servers(self) -> Sequence[McpServerReference]:
        return self._servers


def build_configured_mcp_catalog(
    settings: Settings,
    *,
    scenic_data_path: str = "data/mock/scenic_spots.json",
) -> ConfiguredMcpCatalog:
    """Build a sanitized catalog and distinguish configured from missing credentials."""
    config = build_config_from_settings(settings, scenic_data_path=scenic_data_path)
    statuses: dict[str, McpConnectionStatus] = {
        "amap": "configured" if settings.amap_api_key.strip() else "unconfigured",
        "weather": "configured" if settings.qweather_api_key.strip() else "unconfigured",
        "scenic": "configured" if scenic_data_path.strip() else "unconfigured",
    }
    return ConfiguredMcpCatalog(config, statuses=statuses)


async def mcp_catalog_event(
    catalog: McpCatalogPort,
    *,
    session_id: str,
    run_id: str,
) -> RunEvent:
    """Project only bounded server metadata into the durable public timeline."""
    servers = await catalog.list_servers()
    return RunEvent(
        kind="harness",
        status="completed",
        payload={
            "type": "mcp_catalog_updated",
            "runtime_profile": "deerflow_v2",
            "session_id": session_id,
            "run_id": run_id,
            "servers": [
                {
                    "name": server.name,
                    "transport": server.transport,
                    "status": server.status,
                    "tool_names": list(server.tool_names),
                }
                for server in servers
            ],
        },
        event_id=f"harness:{run_id}:mcp-catalog",
    )


__all__ = [
    "ConfiguredMcpCatalog",
    "build_configured_mcp_catalog",
    "mcp_catalog_event",
]
