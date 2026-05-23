"""
Briefcase Module - Briefcase document organization.

Public API:
    from app.modules.briefcase import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
