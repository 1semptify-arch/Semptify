"""
Legal Analysis Module - Legal document analysis and insights.

Public API:
    from app.modules.legal_analysis import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
