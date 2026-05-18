"""
Legal Trails Module -- Legal case trails and precedents.

Public API:
    from app.modules.legal_trails import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
