"""
register_local_ai — Single entry point to wire the local AI module into a FastAPI app.

Usage:
    from app.modules.local_ai import register_local_ai, LocalAIConfig

    config = LocalAIConfig(...)
    register_local_ai(app, config)
"""

import logging
from fastapi import FastAPI

from app.modules.local_ai.config import LocalAIConfig
from app.modules.local_ai.router import create_router

logger = logging.getLogger(__name__)


def register_local_ai(app: FastAPI, config: LocalAIConfig) -> None:
    """
    Wire the local AI module into the FastAPI application.

    This:
    1. Creates the AI router with all routes
    2. Includes the router in the app
    3. Logs the registration

    After this call, the app has:
    - Chat completion endpoint ({prefix}/chat)
    - Analysis endpoint ({prefix}/analyze)
    - Summarization endpoint ({prefix}/summarize)
    - Health check endpoint ({prefix}/health)
    """
    # Create and include router
    router = create_router(config)
    app.include_router(router)

    logger.info(
        "Local AI module registered: product=%s prefix=%s model=%s endpoint=%s",
        config.product_name,
        config.route_prefix,
        config.model_name,
        config.api_endpoint,
    )
