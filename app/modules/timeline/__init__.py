"""
Timeline Module — Unified chronological event tracking.

Public API:
    from app.modules.timeline import MANIFEST, router
    register_module(app, MANIFEST)

Endpoints (under /api/timeline):
    GET /view      — Unified timeline view with filtering
    GET /items     — List timeline items
    POST /items    — Create timeline event
    GET /export    — Export timeline data
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
