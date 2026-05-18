"""
Emotion Engine Module -- Emotional intelligence analysis.

Public API:
    from app.modules.emotion import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
