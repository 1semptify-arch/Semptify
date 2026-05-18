"""
Batch Operations Module -- Bulk document management.

Public API:
    from app.modules.batch import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
