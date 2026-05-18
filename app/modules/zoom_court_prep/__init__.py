"""
Zoom Court Prep Module -- Zoom court preparation tools.

Public API:
    from app.modules.zoom_court_prep import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
