"""
register_onboarding — Single entry point to wire the onboarding module into a FastAPI app.

Usage:
    from app.modules.onboarding import register_onboarding, OnboardingConfig

    config = OnboardingConfig(...)
    register_onboarding(app, config)
"""

import logging
from fastapi import FastAPI

from app.modules.onboarding.config import OnboardingConfig
from app.modules.onboarding.router import create_router
from app.modules.onboarding.middleware import OnboardingGateMiddleware

logger = logging.getLogger(__name__)


def register_onboarding(app: FastAPI, config: OnboardingConfig) -> None:
    """
    Wire the onboarding module into the FastAPI application.

    This:
    1. Creates the onboarding router with all routes
    2. Includes the router in the app
    3. Adds the gate enforcement middleware

    After this call, the app has:
    - All onboarding page routes ({prefix}/)
    - OAuth initiation and callback ({prefix}/auth/, {prefix}/callback/)
    - Vault API routes ({prefix}/api/vault/)
    - Gate enforcement middleware
    """
    # Create and include router
    router = create_router(config)
    app.include_router(router)

    # Add gate middleware only when not already covered by StorageRequirementMiddleware.
    # When both run together they race and cause redirect loops.
    if config.enable_gate_middleware:
        app.add_middleware(OnboardingGateMiddleware, config=config)
        logger.info("OnboardingGateMiddleware registered for prefix=%s", config.route_prefix)
    else:
        logger.info(
            "OnboardingGateMiddleware SKIPPED (enable_gate_middleware=False) — "
            "gate enforcement delegated to StorageRequirementMiddleware"
        )

    logger.info(
        "Onboarding module registered: product=%s prefix=%s providers=%s gates=%s",
        config.product_name,
        config.route_prefix,
        config.allowed_providers,
        config.gates,
    )
