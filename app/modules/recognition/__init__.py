"""
Document Recognition Module -- AI document recognition.

Public API:
    from app.modules.recognition import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
