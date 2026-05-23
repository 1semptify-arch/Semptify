"""
Complaint Wizard Module -- Regulatory complaint filing.

Public API:
    from app.modules.complaints import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
