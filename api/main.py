"""FastAPI app factory."""

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from agents.graph import build_graph
from api import routes, ws
from core.config.settings import get_settings
from core.llm import create_llm
from mcp_servers.scenic.client import ScenicClient
from mcp_servers.weather.client import WeatherClient

logger = logging.getLogger(__name__)
DEFAULT_PLANNING_MODEL = "doubao:Doubao-Seed-2.0-pro"


def _planning_model_spec(configured_model: str) -> str:
    """Resolve planning model specs with a demo-safe default."""
    return configured_model if ":" in configured_model else DEFAULT_PLANNING_MODEL


def create_runtime_graph() -> Any | None:
    """Build the production graph from local settings, degrading when config is incomplete."""
    try:
        settings = get_settings()
        repo_root = Path(__file__).resolve().parent.parent
        model_spec = _planning_model_spec(settings.llm_model)
        planning_llm = create_llm(model_spec)
        budget_llm = create_llm(model_spec)
        weather_client = WeatherClient(
            api_key=settings.qweather_api_key,
            base_url=settings.qweather_base_url,
            geo_url=settings.qweather_geo_url,
        )
        scenic_client = ScenicClient(
            data_path=str(repo_root / "data" / "mock" / "scenic_spots.json")
        )
        return build_graph(
            weather_client=weather_client,
            scenic_client=scenic_client,
            planning_llm=planning_llm,
            budget_llm=budget_llm,
        )
    except Exception as exc:
        logger.warning("Runtime graph unavailable; API will require injected graph: %s", exc)
        return None


def create_app(graph: Any | None = None) -> FastAPI:
    """Create the TourSwarm API app."""
    app = FastAPI(title="TourSwarm API")
    app.state.graph = graph
    app.include_router(routes.router)
    app.include_router(ws.router)
    return app


app = create_app(graph=create_runtime_graph())
