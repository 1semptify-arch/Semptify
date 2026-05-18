"""
Development Tools Module -- Internal development tools.

Public API:
    from app.modules.development import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
