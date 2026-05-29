"""
Law Library Module - Law library search and reference.

Public API:
    from app.modules.law_library import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router, page_router

__all__ = ["MANIFEST", "router", "page_router"]
