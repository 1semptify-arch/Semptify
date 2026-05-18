"""
Enterprise Dashboard Module -- Enterprise analytics dashboard.

Public API:
    from app.modules.enterprise_dashboard import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
