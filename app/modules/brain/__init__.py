"""
Brain Module — Positronic Brain central intelligence hub.

Public API:
    from app.modules.brain import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)

Endpoints (under /brain):
    GET  /status     — Brain system status
    GET  /modules    — List connected modules
    GET  /state      — Shared state
    PUT  /state      — Update state
    POST /think      — Brain analysis
    POST /workflow   — Trigger workflow
    POST /event      — Emit event
    WS   /ws         — WebSocket connection
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
