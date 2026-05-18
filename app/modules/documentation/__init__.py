"""
Documentation Module -- API and system documentation.

Public API:
    from app.modules.documentation import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
