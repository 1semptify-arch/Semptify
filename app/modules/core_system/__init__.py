"""
Core System Module - Core system infrastructure.

Public API:
    from app.modules.core_system import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
