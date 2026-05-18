"""
Data Export/Import Module -- GDPR-compliant data export/import.

Public API:
    from app.modules.export_import import MANIFEST, router
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
