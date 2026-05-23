"""
Zoom Courtroom Module -- Zoom court video integration.

Public API:
    from app.modules.zoom_court import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
