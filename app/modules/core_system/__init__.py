"""
Core System Module - Core system infrastructure.

Public API:
    from app.modules.core_system import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
