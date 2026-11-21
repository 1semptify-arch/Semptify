"""Regression tests: slowapi ``default_limits`` on lazily-included routers.

FastAPI 0.141 made ``include_router`` lazy — ``app.routes`` holds
``_IncludedRouter`` proxy nodes with no ``endpoint`` attribute and an empty
``matches()`` child_scope. Stock ``SlowAPIMiddleware`` therefore resolved no
handler for any lazily-included endpoint and ``_should_exempt`` skipped the
request, so the global ``default_limits`` never engaged (proven live: 210
same-path requests, zero 429s). ``LazyRouterSlowAPIMiddleware`` fixes handler
resolution via ``effective_route_contexts()``.

These tests build a minimal app rather than importing the Semptify app so the
failure mode (FastAPI/slowapi version interaction) is exercised in isolation.
"""

import pytest
from fastapi import APIRouter, FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.rate_limit import LazyRouterSlowAPIMiddleware, find_route_handler


def _build_app(default_limits: list[str]):
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=default_limits,
        storage_uri="memory://",
    )
    app = FastAPI()
    app.state.limiter = limiter
    app.add_middleware(LazyRouterSlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    return app, limiter


def test_default_limits_apply_to_included_router():
    """Undecorated endpoint on a lazily-included router must hit 429."""
    app, _ = _build_app(["5/minute"])
    router = APIRouter()

    @router.get("/ping")
    def ping():
        return {"ok": True}

    app.include_router(router, prefix="/api")
    client = TestClient(app)

    codes = [client.get("/api/ping").status_code for _ in range(8)]
    assert codes[:5] == [200] * 5
    assert codes[5:] == [429] * 3


def test_nested_included_router_is_limited():
    """Routers included inside included routers also get default limits."""
    app, _ = _build_app(["5/minute"])
    outer = APIRouter()
    inner = APIRouter()

    @inner.get("/deep")
    def deep():
        return {"ok": True}

    outer.include_router(inner, prefix="/nested")
    app.include_router(outer, prefix="/api")
    client = TestClient(app)

    codes = [client.get("/api/nested/deep").status_code for _ in range(7)]
    assert codes[5:] == [429] * 2


def test_decorated_route_uses_its_own_limit_not_double_counted():
    """A route with @limiter.limit keeps its own limit; the middleware must
    resolve it (so it is skipped in middleware, not charged against defaults)."""
    app, limiter = _build_app(["5/minute"])
    router = APIRouter()

    @router.get("/decorated")
    @limiter.limit("2/minute")
    def decorated(request: Request):
        return {"ok": True}

    app.include_router(router, prefix="/api")
    client = TestClient(app)

    codes = [client.get("/api/decorated").status_code for _ in range(4)]
    assert codes == [200, 200, 429, 429]

    # Handler resolution must land on a name registered in _route_limits so
    # the middleware exempts it (the decorator enforces the limit itself).
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/decorated",
        "root_path": "",
        "path_params": {},
        "headers": [],
        "query_string": b"",
        "app": app,
    }
    handler = find_route_handler(app.routes, scope)
    name = f"{handler.__module__}.{handler.__name__}"
    assert name in limiter._route_limits


def test_exempt_route_is_never_limited():
    """@limiter.exempt must be honoured through the lazy proxy."""
    app, limiter = _build_app(["5/minute"])
    router = APIRouter()

    @router.get("/exempted")
    @limiter.exempt
    def exempted():
        return {"ok": True}

    app.include_router(router, prefix="/api")
    client = TestClient(app)

    codes = [client.get("/api/exempted").status_code for _ in range(8)]
    assert codes == [200] * 8


def test_directly_registered_route_still_limited():
    """Regular (non-included) routes keep working exactly as before."""
    app, _ = _build_app(["5/minute"])

    @app.get("/direct")
    def direct():
        return {"ok": True}

    client = TestClient(app)
    codes = [client.get("/direct").status_code for _ in range(7)]
    assert codes[5:] == [429] * 2


def test_unmatched_path_is_not_limited():
    """404s resolve no handler and stay unthrottled (stock behaviour)."""
    app, _ = _build_app(["1/minute"])
    client = TestClient(app)
    codes = [client.get("/no-such-path").status_code for _ in range(4)]
    assert codes == [404] * 4


def test_find_route_handler_returns_none_on_miss():
    """Resolver contract: None when nothing FULL-matches."""
    app, _ = _build_app(["100/minute"])
    router = APIRouter()

    @router.get("/x")
    def x():
        return {"ok": True}

    app.include_router(router, prefix="/api")
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/missing",
        "root_path": "",
        "path_params": {},
        "headers": [],
        "query_string": b"",
        "app": app,
    }
    assert find_route_handler(app.routes, scope) is None
