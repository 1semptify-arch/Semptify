"""
Document Preview Module - Multi-format document preview.

Public API:
    from app.modules.preview import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
