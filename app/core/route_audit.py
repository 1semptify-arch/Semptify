"""Post-startup public-route audit.

Walks ``fastapi_app.routes`` after all mounting is complete and flags any
actionable public route that is not covered by a registered
``FunctionGroupContract``'s ``allowed_routes`` / ``allowed_prefixes``.

This closes the ``/debug/seed-test-user`` class of gap: an ad-hoc route
slipping onto the public surface with no contract, no review, and nobody
noticing until an audit stumbles across it.

Scope: only "actionable" routes are flagged — API paths (``/api/...``) and
any non-GET method anywhere. Plain GET pages (GUI guides, static HTML,
marketing pages) are intentionally out of scope: they are public by design
and covered by page-level review, not module contracts.

Non-fatal by design (same contract-loader convention): one warning per
flagged route plus a summary line. Set ``ROUTE_AUDIT_STRICT=1`` to make
flagged routes a hard startup failure — useful in CI.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI

logger = logging.getLogger(__name__)

_SKIP_METHODS = {"HEAD", "OPTIONS"}
# Mounts and infra paths that are public plumbing, not module surface.
_INFRA_PREFIXES = ("/static", "/assets", "/docs", "/openapi", "/redoc")


def _contract_coverage() -> tuple[set[str], tuple[str, ...]]:
    """Union of every registered contract's allowed_routes + allowed_prefixes."""
    from app.core.module_contracts import contract_registry

    routes: set[str] = set()
    prefixes: set[str] = set()
    for contract in contract_registry.list_contracts():
        routes.update(contract.allowed_routes)
        prefixes.update(contract.allowed_prefixes)
    return routes, tuple(p.rstrip("/") for p in prefixes)


def _is_covered(path: str, routes: set[str], prefixes: tuple[str, ...]) -> bool:
    if path in routes:
        return True
    return any(path == p or path.startswith(p + "/") for p in prefixes)


def _is_actionable(path: str, methods: set[str]) -> bool:
    """A public route is actionable if it is an API path or does mutations."""
    if path.startswith(_INFRA_PREFIXES):
        return False
    if path.startswith("/api/"):
        return True
    return bool(methods - {"GET"} - _SKIP_METHODS)


def scan_public_routes(app: FastAPI) -> list[dict[str, Any]]:
    """Audit mounted routes; log (and return) uncovered public routes.

    Returns a list of {path, methods} dicts for public routes that are
    actionable and have no contract coverage. Call once, after all routers
    are mounted (end of create_app).
    """
    from app.core.storage_middleware import is_public_path

    allowed_routes, allowed_prefixes = _contract_coverage()

    flagged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for route in getattr(app, "routes", []):
        path = getattr(route, "path", None)
        if not path or "{" in path:  # parameterized paths audited via prefix
            continue
        methods = {m for m in getattr(route, "methods", set()) if m not in _SKIP_METHODS}
        if not methods:
            continue
        for method in sorted(methods):
            key = (method, path)
            if key in seen:
                continue
            seen.add(key)
            if not is_public_path(path):
                continue
            if not _is_actionable(path, methods):
                continue
            if _is_covered(path, allowed_routes, allowed_prefixes):
                continue
            flagged.append({"path": path, "method": method})

    if flagged:
        for item in flagged:
            logger.warning(
                "Public route with no contract coverage: %s %s — register it in a "
                "FunctionGroupContract (allowed_routes) or add an auth gate.",
                item["method"],
                item["path"],
            )
        summary = (
            f"Route audit: {len(flagged)} uncovered public route(s). "
            "See warnings above."
        )
        if os.getenv("ROUTE_AUDIT_STRICT", "").lower() in ("1", "true", "yes"):
            raise RuntimeError(summary)
        logger.warning(summary)
    else:
        logger.info("Route audit: all actionable public routes have contract coverage.")

    return flagged
