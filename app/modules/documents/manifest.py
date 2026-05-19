"""
Documents Module Manifest

Self-contained SDK module for document management, processing,
and law cross-referencing. All uploads go to vault first.

Capabilities:
- Document upload, certification, retrieval
- OCR and AI analysis
- Law engine cross-referencing
- Vault integration
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="documents",
    display_name="Document System",
    description="Upload, certify, organize tenant documents with OCR and AI analysis",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER, ModuleCapability.DOCUMENT),
    router_module="app.modules.documents.router",
    tags=("Documents",),
)
