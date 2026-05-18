"""
Modular Components Module - Modular component system integration.

Public API:
    from app.modules.components import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
