"""
Health Module — System observability and monitoring.

Public API:
    from app.modules.health import MANIFEST, router
    register_module(app, MANIFEST)

Endpoints:
    /healthz        — Liveness probe
    /livez          — Kubernetes liveness alias
    /readyz         — Readiness probe (checks DB, dirs, AI)
    /metrics        — Prometheus metrics
    /metrics/json   — JSON metrics
    /system-dashboard — Visual status dashboard
    /api-summary    — JSON capability summary
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
