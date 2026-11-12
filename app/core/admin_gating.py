"""Tailscale/private-network gating for admin routes.

No public-internet login path for admin. Allowed ranges default to Tailscale CGNAT
(100.64.0.0/10), RFC1918 private networks, and localhost. Override with
ADMIN_IP_RANGES env var.
"""

import ipaddress
import logging

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.admin_elevation import ELEVATION_COOKIE_NAME, verify_elevation_cookie
from app.core.config import get_settings

logger = logging.getLogger("semptify.admin_gating")


def _parse_networks(raw: str) -> list[ipaddress.ip_network]:
    """Parse a comma-separated list of CIDR ranges."""
    networks = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            networks.append(ipaddress.ip_network(part, strict=False))
        except ValueError as exc:
            logger.warning("Ignoring invalid admin IP range %r: %s", part, exc)
    return networks


def _get_client_ip(request: Request) -> str:
    """Return the most useful client IP for admin-network checks.

    Prefers the rightmost non-local address in X-Forwarded-For, then X-Real-Ip,
    then the direct transport client. This is safe only when the app is behind a
    trusted reverse proxy; in a Tailscale setup the subnet router or ingress node
    sets these headers.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        for candidate in reversed(forwarded.split(",")):
            candidate = candidate.strip()
            if candidate and candidate not in ("127.0.0.1", "::1", "localhost"):
                return candidate

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    return request.client.host if request.client else "unknown"


def is_admin_network(client_ip: str) -> bool:
    """Return True if the client IP is in an allowed admin network."""
    settings = get_settings()
    networks = _parse_networks(settings.admin_ip_ranges)
    if not networks:
        return True  # No restrictions configured (development only)

    try:
        addr = ipaddress.ip_address(client_ip)
    except ValueError:
        return False

    for network in networks:
        if addr in network:
            return True
    return False


async def require_admin_network(request: Request) -> None:
    """FastAPI dependency that enforces admin-network gating.

    Raises HTTPException(404) to hide the existence of admin endpoints.
    """
    client_ip = _get_client_ip(request)
    if not is_admin_network(client_ip):
        logger.warning("Admin access denied for IP %s", client_ip)
        raise HTTPException(status_code=404, detail="Not Found")


class AdminNetworkMiddleware(BaseHTTPMiddleware):
    """Middleware that returns 404 for any /admin path from a non-admin network.

    Run this as the outermost middleware so admin routes are blocked before any
    storage or auth checks run.

    Two carve-outs keep admin usable from dynamic IPs (Brad has no static IP):
    the login surface stays reachable from anywhere — it is how a credential
    is obtained — and any request carrying a valid elevation cookie passes,
    since the cookie itself is the admin credential (password + TOTP issued).
    """

    ADMIN_PREFIX = "/admin"

    _OPEN_PATHS = frozenset(
        {"/admin/login", "/admin/api/login-step1", "/admin/api/login-step2"}
    )

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith(self.ADMIN_PREFIX):
            return await call_next(request)

        client_ip = _get_client_ip(request)
        if is_admin_network(client_ip) or path.rstrip("/") in self._OPEN_PATHS:
            return await call_next(request)

        elev_cookie = request.cookies.get(ELEVATION_COOKIE_NAME)
        if verify_elevation_cookie(str(elev_cookie) if elev_cookie else None):
            return await call_next(request)

        logger.warning("Admin request blocked for IP %s", client_ip)
        return _not_found()


def _not_found():
    from starlette.responses import JSONResponse

    return JSONResponse(status_code=404, content={"detail": "Not Found"})
