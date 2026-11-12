"""Tests for AdminNetworkMiddleware — IP gate + dynamic-IP carve-outs.

Policy under test (Brad, 2026-10-12): admin must stay usable from dynamic
IPs. The login surface is reachable from any IP (it is how a credential
is obtained); any other /admin path passes for a foreign IP only when the
request carries a valid elevation cookie. Allowlisted IPs pass always.
"""

import pytest
from starlette.requests import Request
from starlette.responses import Response

import app.core.admin_gating as gating
from app.core.admin_elevation import ELEVATION_COOKIE_NAME, issue_elevation_cookie
from app.core.admin_gating import AdminNetworkMiddleware

FOREIGN_IP = "203.0.113.9"


def _request(path: str, client_ip: str = FOREIGN_IP, cookies: dict | None = None) -> Request:
    headers = []
    if cookies:
        headers.append(
            (b"cookie", "; ".join(f"{k}={v}" for k, v in cookies.items()).encode())
        )
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": headers,
        "client": (client_ip, 12345),
        "query_string": b"",
        "server": ("test", 80),
        "scheme": "http",
    }
    return Request(scope)


async def _ok(_request: Request) -> Response:
    return Response("ok")


@pytest.fixture
def foreign_ip(monkeypatch):
    """Simulate a client outside ADMIN_IP_RANGES."""
    monkeypatch.setattr(gating, "is_admin_network", lambda _ip: False)


@pytest.fixture
def admin_ip(monkeypatch):
    monkeypatch.setattr(gating, "is_admin_network", lambda _ip: True)


async def test_non_admin_path_always_passes(foreign_ip):
    mw = AdminNetworkMiddleware(app=None)
    resp = await mw.dispatch(_request("/api/voice-posts"), _ok)
    assert resp.status_code == 200


@pytest.mark.parametrize(
    "path",
    ["/admin/login", "/admin/api/login-step1", "/admin/api/login-step2"],
)
async def test_login_surface_open_to_foreign_ip(foreign_ip, path):
    mw = AdminNetworkMiddleware(app=None)
    resp = await mw.dispatch(_request(path), _ok)
    assert resp.status_code == 200


async def test_foreign_ip_blocked_without_cookie(foreign_ip):
    mw = AdminNetworkMiddleware(app=None)
    resp = await mw.dispatch(_request("/admin/public-voice"), _ok)
    assert resp.status_code == 404


async def test_foreign_ip_passes_with_elevation_cookie(foreign_ip):
    cookie = issue_elevation_cookie("test-uid")
    mw = AdminNetworkMiddleware(app=None)
    resp = await mw.dispatch(
        _request("/admin/public-voice", cookies={ELEVATION_COOKIE_NAME: cookie}), _ok
    )
    assert resp.status_code == 200


async def test_foreign_ip_blocked_with_tampered_cookie(foreign_ip):
    mw = AdminNetworkMiddleware(app=None)
    resp = await mw.dispatch(
        _request("/admin/public-voice", cookies={ELEVATION_COOKIE_NAME: "bad.sig"}), _ok
    )
    assert resp.status_code == 404


async def test_allowlisted_ip_passes_without_cookie(admin_ip):
    mw = AdminNetworkMiddleware(app=None)
    resp = await mw.dispatch(_request("/admin/public-voice"), _ok)
    assert resp.status_code == 200
