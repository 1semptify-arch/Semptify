"""Unified page router module — serves all manifest template pages.

This module registers a single router that dynamically serves every template
page declared in the page manifest. Each route applies the contract-based guard
(auth + role check) and renders the Jinja2 template with standard context.

Pages that already have dedicated route handlers in main.py or other modules
are skipped — this router only registers routes for pages that aren't already
served elsewhere.
"""
from .router import router

__all__ = ["router"]
