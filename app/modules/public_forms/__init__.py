"""
Public Forms Module - Public court form access.

Public API:
    from app.modules.public_forms import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
