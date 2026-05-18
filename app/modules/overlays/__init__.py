"""
Document Overlays Module -- Non-destructive document annotation.

Public API:
    from app.modules.overlays import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
