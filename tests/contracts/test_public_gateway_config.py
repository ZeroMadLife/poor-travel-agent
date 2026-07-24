"""Public gateway host-routing contracts without application runtime imports."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_public_gateway_has_a_bounded_direct_ip_fallback() -> None:
    caddyfile = (ROOT / "infra/proxy/Caddyfile.public").read_text(encoding="utf-8")

    ip_site_start = caddyfile.index("http://121.40.185.188")
    catch_all_start = caddyfile.index("http://:8081")
    ip_site = caddyfile[ip_site_start:catch_all_start]
    catch_all_site = caddyfile[catch_all_start : caddyfile.index("sagecompanion.top")]

    assert "import /etc/caddy/public-agent" in ip_site
    assert "import /etc/caddy/public-static" in ip_site
    assert "reverse_proxy api:" not in ip_site
    assert "redir" not in ip_site
    assert "@health path /healthz" in catch_all_site
    assert "redir https://{host}{uri} permanent" in catch_all_site
