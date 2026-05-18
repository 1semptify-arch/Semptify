"""
Housing Accountability Module -- Housing accountability tracking.

Public API:
    from app.modules.housing_accountability import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import accountability_router as router

__all__ = ["MANIFEST", "router"]
