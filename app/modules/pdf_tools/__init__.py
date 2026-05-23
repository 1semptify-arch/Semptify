"""
PDF Tools Module - PDF manipulation and generation tools.

Public API:
    from app.modules.pdf_tools import MANIFEST, router
import logging
logger = logging.getLogger(__name__)
    register_module(app, MANIFEST)
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
