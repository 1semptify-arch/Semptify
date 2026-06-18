"""
Advanced Security Module - 2FA and session management.

Public API:
    from app.modules.security import MANIFEST, router
    register_module(app, MANIFEST)
"""

import logging
logger = logging.getLogger(__name__)

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
