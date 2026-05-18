"""
Location Module -- Location-based services.

Public API:
    from app.modules.location import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
