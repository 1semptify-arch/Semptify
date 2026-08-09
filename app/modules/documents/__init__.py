"""
Documents Module — Document management, processing, and law cross-referencing.

Public API:
    from app.modules.documents import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)

Endpoints:
    POST /api/documents/upload         — Upload document to vault
    GET  /api/documents                — List documents
    GET  /api/documents/{id}           — Get document
    GET  /api/documents/{id}/analysis  — AI analysis
    GET  /api/documents/{id}/laws      — Cross-referenced statutes
"""

from .manifest import MANIFEST
from .router import router
from .service import *  # noqa: F401,F403

__all__ = ["MANIFEST", "router"]
