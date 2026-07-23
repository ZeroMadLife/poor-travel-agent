"""Trusted public proxy identity coverage."""

from public_agent.client_identity import PublicClientIdentityResolver


def test_identity_configuration_parses_bounded_proxy_networks() -> None:
    resolver = PublicClientIdentityResolver.from_cidrs("172.16.0.0/12, fd00::/8")

    assert len(resolver.trusted_proxy_cidrs) == 2
    assert resolver.header_name == "X-Sage-Public-Client-IP"
