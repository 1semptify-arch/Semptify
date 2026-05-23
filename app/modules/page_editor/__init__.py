"""
Page Editor Module -- Interactive page editor for templates.

Public API:
    from app.modules.page_editor import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
