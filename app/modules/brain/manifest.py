"""
Brain Module Manifest

Self-contained SDK module for the Positronic Brain.
REST API and WebSocket endpoints for central intelligence hub.

Capabilities:
- Brain status and module listing
- Shared state management
- Workflow triggering
- Event emission
- WebSocket real-time communication
"""

import logging

from app.sdk import ModuleCapability, ModuleManifest, ProductTier

logger = logging.getLogger(__name__)


MANIFEST = ModuleManifest(
    name="brain",
    display_name="Positronic Brain",
    description="Central intelligence hub with REST API and WebSocket endpoints",
    version="1.0.0",
    tier=ProductTier.RESEARCH,
    capabilities=(ModuleCapability.ROUTER, ModuleCapability.MESH),
    router_module="app.modules.brain.router",
    prefix="/brain",
    tags=("Positronic Brain",),
)
