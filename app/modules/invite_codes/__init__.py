"""
Invite Codes Module -- Invite code management.

Public API:
    from app.modules.invite_codes import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
