"""
State Laws Module - State law lookup and reference.

Public API:
    from app.modules.state_laws import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
