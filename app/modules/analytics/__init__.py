"""
Analytics Module -- Usage and performance analytics.

Public API:
    from app.modules.analytics import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
