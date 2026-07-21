from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_local_searxng_stack_is_loopback_only_and_json_enabled() -> None:
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text())
    service = compose["services"]["searxng"]

    assert service["ports"] == ["127.0.0.1:${SAGE_SEARXNG_PORT:-8088}:8080"]
    assert service["image"].startswith("searxng/searxng:")
    assert service["image"] != "searxng/searxng:latest"

    settings = yaml.safe_load((REPO_ROOT / "infra/dev/searxng/settings.yml").read_text())
    assert "json" in settings["search"]["formats"]
    assert settings["server"]["limiter"] is False
    assert settings["engines"] == [
        {
            "name": "sogou",
            "engine": "sogou",
            "shortcut": "sogou",
            "disabled": False,
        }
    ]
