"""
Document Registry Module -- Document registry management.

Public API:
    from app.modules.registry import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
