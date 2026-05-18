"""
Unified Overlays Module -- Unified overlay system.

Public API:
    from app.modules.unified_overlays import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
