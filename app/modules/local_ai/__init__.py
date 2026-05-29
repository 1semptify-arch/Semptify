"""
Semptify Local AI Module — Self-contained local AI integration.

Usage:
    from app.modules.local_ai import register_local_ai, LocalAIConfig
    import logging
    logger = logging.getLogger(__name__)

    config = LocalAIConfig(
        product_name="Semptify Local AI",
        model_name="llama-3-8b",
        api_endpoint="http://localhost:11434/api/generate",
        max_tokens=2048,
        temperature=0.7,
    )
    register_local_ai(app, config)
"""

from app.modules.local_ai.config import LocalAIConfig
from app.modules.local_ai.register import register_local_ai

__all__ = ["LocalAIConfig", "register_local_ai"]
