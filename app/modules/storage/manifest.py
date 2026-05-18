"""
Storage Module Manifest

Self-contained SDK module for OAuth storage authentication.
- OAuth flows for Google Drive, Dropbox, OneDrive
- Token management and encryption
- User session handling
- Provider connection status
- Reconnect and logout flows
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="storage",
    display_name="Storage Auth",
    description="OAuth2 flows for Google Drive, Dropbox, and OneDrive storage",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER, ModuleCapability.CONTRACT),
    router_module="app.modules.storage.router",
    tags=("Storage Auth",),
)
