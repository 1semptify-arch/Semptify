"""
Page Editor Module -- Interactive page editor for templates.

Public API:
    from app.modules.page_editor import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
