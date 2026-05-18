"""
WebSocket Events Module - Real-time WebSocket event streaming.

Public API:
    from app.modules.websocket import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
