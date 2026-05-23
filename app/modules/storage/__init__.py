"""
Storage Module — OAuth storage authentication.

Public API:
    from app.modules.storage import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)

Endpoints (under /storage):
    GET  /               — Storage entry / provider selection
    GET  /callback       — OAuth callback
    GET  /status         — Connection status
    GET  /reconnect      — Reconnect flow
    GET  /logout         — Logout and reset
    POST /disconnect     — Disconnect provider
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
