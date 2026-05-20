"""
External Mappings Module -- Bridge to external systems

Public API:
    from app.modules.external_mappings import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import mappings_router as router

__all__ = ["MANIFEST", "router"]
