"""
Calendar Module -- Calendar integration.

Public API:
    from app.modules.calendar import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
