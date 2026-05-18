"""
RISC Module - RISC assessment routing.

Public API:
    from app.modules.risc import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
