"""Deferred router registration for cold-boot-constrained deploys.

Render free-tier port-scan kills the instance if the TCP port is not bound
quickly. Uvicorn binds the socket only AFTER ``config.load()`` (the module
import that runs ``create_app()``) AND the lifespan startup complete — so
every eager ``register_tiers()`` / ``load_all_contracts()`` import and every
staged-setup second counts against the scan window. Cold import measured
~60s on the free tier (BUILD_STATE.md 2026-10-31, exit-3 crash loop during
the Neon quota outage).

This module provides the "lazy router imports" half of the fix:

- ``defer_router_registration()`` — called from ``create_app()`` in place of
  ``register_tiers()``. Stashes the enabled tiers on ``app.state`` and
  installs the warmup gate middleware, so the app factory returns without
  importing ~50 router modules.
- ``run_deferred_registration(app)`` — spawned as a background task at the
  top of the lifespan. Runs the real ``register_tiers`` + contract load +
  route audit inside a thread executor so imports cannot block the event
  loop, then flips ``app.state.routers_ready``.
- The warmup gate short-circuits non-exempt requests with ``503 +
  Retry-After`` (HTML self-refreshing page for browsers, JSON for API
  clients) until ``routers_ready`` is set. Static assets, ``/health``, and
  the eagerly-registered public pages keep serving during warmup — Render's
  port check and health probes see a live service immediately.

Activation:
    Auto-on when ``DEPLOY_TARGET=render_mvp`` (the Render free-tier build).
    ``SEMPTIFY_LAZY_ROUTERS=1`` forces it on (local testing);
    ``SEMPTIFY_LAZY_ROUTERS=0`` forces it off (rollback escape hatch —
    same pattern as ``ENABLE_HEAVY_SERVICES=false``).
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING

from fastapi.responses import HTMLResponse, JSONResponse

if TYPE_CHECKING:
    from fastapi import FastAPI, Request

logger = logging.getLogger(__name__)

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def lazy_routers_enabled() -> bool:
    """Whether deferred router registration is active for this process."""
    raw = os.getenv("SEMPTIFY_LAZY_ROUTERS", "").strip().lower()
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    from app.core.product_manifest import is_mvp_deploy

    return is_mvp_deploy()


# Paths that must keep serving during warmup: everything the port scan,
# health probes, and the warmup page itself need, plus assets used by the
# eagerly-registered public pages.
_WARMUP_EXEMPT_PREFIXES = (
    "/health",
    "/static",
    "/assets",
    "/public",
    "/favicon.ico",
    "/.well-known",
    "/components/footer",
)

_WARMUP_EXEMPT_PATHS = frozenset(
    {
        "/",
        "/welcome.html",
        "/activate-vault",
    }
)

_portal_paths_cache: frozenset[str] | None = None


def _portal_page_paths() -> frozenset[str]:
    """Portal-registry public pages — eagerly registered, safe during warmup."""
    global _portal_paths_cache
    if _portal_paths_cache is None:
        try:
            from app.modules.portal.pages import portal_pages

            _portal_paths_cache = frozenset(p.path for p in portal_pages.PAGES)
        except Exception as exc:  # noqa: BLE001 — never let the gate fail closed on itself
            logger.warning("Warmup gate: portal page list unavailable (%s)", exc)
            _portal_paths_cache = frozenset()
    return _portal_paths_cache


_WARMUP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="3">
  <title>Semptify is starting</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
           background: #f7f5f0; color: #2b2b2b; display: flex; min-height: 100vh;
           align-items: center; justify-content: center; margin: 0; padding: 1rem; }
    .card { max-width: 30rem; background: #fff; padding: 2rem; border-radius: 10px;
            box-shadow: 0 1px 4px rgba(0,0,0,.08); font-size: 1.05rem; line-height: 1.6; }
    a { color: #2c5aa0; }
  </style>
</head>
<body>
  <div class="card">
    <p><strong>Semptify is starting up.</strong></p>
    <p>This page retries automatically every few seconds. If it keeps
       happening, you can still <a href="/">go to the home page</a> or
       <a href="/static/public/semptify-help-standalone.html">get help now</a>.</p>
  </div>
</body>
</html>
"""


def _warming_response(request: Request):
    """503 + Retry-While-Starting response for non-exempt warmup requests."""
    headers = {"Retry-After": "3"}
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return HTMLResponse(content=_WARMUP_HTML, status_code=503, headers=headers)
    return JSONResponse(
        status_code=503,
        headers=headers,
        content={
            "detail": "Semptify is starting up — try again in a few seconds.",
            "retry_after_seconds": 3,
        },
    )


def _is_warmup_exempt(request: Request) -> bool:
    path = request.url.path
    if path in _WARMUP_EXEMPT_PATHS:
        return True
    if any(path.startswith(prefix) for prefix in _WARMUP_EXEMPT_PREFIXES):
        return True
    if request.method in ("GET", "HEAD") and path in _portal_page_paths():
        return True
    return False


def defer_router_registration(app: FastAPI, tiers) -> None:
    """Mark routers as deferred and install the warmup gate middleware.

    Called from create_app() instead of register_tiers(). The actual import
    and include_router work runs later in run_deferred_registration().
    """
    app.state.routers_pending = list(tiers)
    app.state.routers_ready = False

    @app.middleware("http")
    async def _warmup_gate(request: Request, call_next):
        if getattr(request.app.state, "routers_ready", True):
            return await call_next(request)
        if _is_warmup_exempt(request):
            return await call_next(request)
        return _warming_response(request)

    logger.info(
        "Lazy routers enabled (SEMPTIFY_LAZY_ROUTERS/DEPLOY_TARGET=render_mvp): "
        "%d tier(s) deferred to post-bind warmup",
        len(tiers),
    )


async def run_deferred_registration(app: FastAPI) -> None:
    """Background warmup: contracts -> routers -> route audit, then open the gate.

    Runs in the default executor because module imports are synchronous and
    CPU-bound — keeping them off the event loop lets the server answer
    /health and static/public requests while routers load.
    """
    tiers = list(app.state.routers_pending)

    def _work():
        from app.core.contract_loader import load_all_contracts
        from app.core.product_manifest import register_tiers
        from app.core.route_audit import scan_public_routes

        contracts = load_all_contracts(enabled_tiers=tiers)
        report = register_tiers(app, *tiers)
        flagged = scan_public_routes(app)
        return report, contracts, flagged

    try:
        loop = asyncio.get_running_loop()
        report, contracts, flagged = await loop.run_in_executor(None, _work)
        app.state.routers_ready = True
        logger.info(
            "Deferred router warmup complete: %s routers registered "
            "(%s contracts loaded, %s uncovered public routes flagged)",
            report.get("registered"),
            contracts.get("loaded"),
            len(flagged),
        )
    except Exception:  # noqa: BLE001 — a warmup failure must not kill the process
        logger.exception(
            "Deferred router registration FAILED — warmup gate stays up; "
            "service will keep returning 503 until this is resolved"
        )
