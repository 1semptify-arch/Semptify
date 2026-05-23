"""
Unified Overlays Module -- Unified overlay system.

Public API:
    from app.modules.unified_overlays import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
