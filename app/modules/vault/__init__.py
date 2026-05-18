"""
Document Vault Module - Document vault management.

Public API:
    from app.modules.vault import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
