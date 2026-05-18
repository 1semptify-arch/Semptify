"""
Global Search Module - Global search across all data.

Public API:
    from app.modules.search import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
