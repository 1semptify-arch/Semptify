"""
Document Delivery Module -- Secure document delivery.

Public API:
    from app.modules.document_delivery import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
