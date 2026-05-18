"""
Zoom Courtroom Module -- Zoom court video integration.

Public API:
    from app.modules.zoom_court import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
