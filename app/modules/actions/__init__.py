"""
Smart Actions Module -- Smart action automation.

Public API:
    from app.modules.actions import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
