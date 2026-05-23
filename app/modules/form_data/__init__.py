"""
Form Data Hub Module -- Centralized form data hub.

Public API:
    from app.modules.form_data import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
