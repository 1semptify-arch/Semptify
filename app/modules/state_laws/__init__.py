"""
State Laws Module - State law lookup and reference.

Public API:
    from app.modules.state_laws import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
