"""
WebSocket Events Module Manifest

Self-contained SDK module for Real-time WebSocket event streaming.
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="websocket",
    display_name="WebSocket Events",
    description="Real-time WebSocket event streaming",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.websocket.router",
    prefix="/ws",
    tags=("WebSocket Events",),
)
