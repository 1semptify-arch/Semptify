"""
Zoom Court Prep Module -- Zoom court preparation tools.

Public API:
    from app.modules.zoom_court_prep import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
