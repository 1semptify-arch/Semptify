"""
Tools Module -- Utility tools API.

Public API:
    from app.modules.tools_api import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
