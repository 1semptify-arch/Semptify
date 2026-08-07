"""
Register Vault Installer Module

Simple registration - just add the routes to the app.
"""

import logging

from fastapi import FastAPI

from .routes import create_router

logger = logging.getLogger(__name__)


def register_vault_installer(app: FastAPI):
    """
    Register the vault installer module.

    This adds simple vault installation endpoints without complex onboarding.
    """
    router = create_router()
    app.include_router(router)

    logger.info("● Vault installer module registered")
