"""
register_local_ai — Single entry point to wire the local AI module into a FastAPI app.

Usage:
    from app.modules.local_ai import register_local_ai, LocalAIConfig

    config = LocalAIConfig(...)
    register_local_ai(app, config)
"""

import logging

from fastapi import FastAPI

from app.core.module_contracts import FunctionGroupContract, register_function_group
from app.modules.local_ai.config import LocalAIConfig
from app.modules.local_ai.router import create_router

logger = logging.getLogger(__name__)

# FunctionGroupContracts for the local AI module.
#
# This module is generic dev-tier tooling: each Semptify product supplies its
# own LocalAIConfig (including route_prefix, default "/local-ai"). It is not
# wired into app.main and has no MANIFEST entry, so these contracts load only
# when all product tiers are enabled (development).

register_function_group(
    FunctionGroupContract(
        module="local_ai",
        group_name="local_ai_health",
        title="Local AI Health (SSOT)",
        description=(
            "CANONICAL health check for the configured local AI backend "
            "(Ollama, LM Studio, etc.). Reports reachability and model status."
        ),
        inputs=(),
        outputs=("status",),
        dependencies=("app.modules.local_ai.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="local_ai",
        group_name="local_ai_chat",
        title="Local AI Chat (SSOT)",
        description=(
            "CANONICAL chat completion against the configured local model. "
            "Request content is caller-supplied and may carry tenant PII."
        ),
        inputs=("messages", "options?"),
        outputs=("response",),
        dependencies=("app.modules.local_ai.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="local_ai",
        group_name="local_ai_analyze",
        title="Local AI Analyze (SSOT)",
        description=(
            "CANONICAL text analysis endpoint. Runs the configured local model "
            "over caller-supplied text, which may contain tenant PII."
        ),
        inputs=("text", "analysis_type?"),
        outputs=("analysis",),
        dependencies=("app.modules.local_ai.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="local_ai",
        group_name="local_ai_summarize",
        title="Local AI Summarize (SSOT)",
        description=(
            "CANONICAL summarization endpoint. Condenses caller-supplied text "
            "via the configured local model; input may contain tenant PII."
        ),
        inputs=("text", "max_length?"),
        outputs=("summary",),
        dependencies=("app.modules.local_ai.router",),
        deterministic=False,
    )
)


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
