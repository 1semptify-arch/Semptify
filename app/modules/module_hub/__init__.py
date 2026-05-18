"""
Module Hub Module -- Central module hub.

Public API:
    from app.modules.module_hub import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
