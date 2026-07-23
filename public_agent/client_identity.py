"""Resolve a privacy-preserving client key behind the bounded public proxy."""

from __future__ import annotations

import hashlib
import ipaddress
from dataclasses import dataclass

from fastapi import Request


class PublicClientIdentityError(ValueError):
    """The trusted proxy did not provide a valid client identity."""


@dataclass(frozen=True, slots=True)
class PublicClientIdentityResolver:
    trusted_proxy_cidrs: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = ()
    header_name: str = "X-Sage-Public-Client-IP"

    @classmethod
    def from_cidrs(
        cls,
        value: str,
        *,
        header_name: str = "X-Sage-Public-Client-IP",
    ) -> PublicClientIdentityResolver:
        networks = tuple(
            ipaddress.ip_network(item.strip(), strict=False)
            for item in value.split(",")
            if item.strip()
        )
        return cls(networks, header_name)

    def resolve(self, request: Request) -> str:
        peer = request.client.host if request.client is not None else "unknown"
        peer_address = _parse_ip(peer)
        if peer_address is not None and any(
            peer_address.version == network.version and peer_address in network
            for network in self.trusted_proxy_cidrs
        ):
            forwarded = request.headers.get(self.header_name, "").strip()
            forwarded_address = _parse_ip(forwarded)
            if forwarded_address is None:
                raise PublicClientIdentityError("trusted proxy client identity is missing")
            identity = forwarded_address.compressed
        else:
            identity = peer_address.compressed if peer_address is not None else peer
        return "client:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]


def _parse_ip(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None
