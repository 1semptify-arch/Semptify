"""
Plugin System Module - Plugin management and registration.

Public API:
    from app.modules.plugins import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
