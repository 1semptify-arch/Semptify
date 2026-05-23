"""
Legal Analysis Module - Legal document analysis and insights.

Public API:
    from app.modules.legal_analysis import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
