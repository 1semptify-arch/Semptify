"""
LocalAIConfig — Product-level configuration for the local AI module.

Each Semptify product provides its own config. The module is generic;
the config makes it specific.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LocalAIConfig:
    """
    Configuration for the local AI module.

    Attributes:
        product_name:          Human-readable product name (shown in UI).
        model_name:            Model identifier (e.g., "llama-3-8b", "mistral-7b").
        api_endpoint:          Local AI API endpoint (e.g., Ollama, LM Studio).
        max_tokens:            Maximum tokens per response.
        temperature:           Sampling temperature (0.0-1.0).
        timeout:               Request timeout in seconds.
        route_prefix:          URL prefix for all AI routes.
        enabled_features:      Features to enable (chat, analysis, summarization).
        system_prompt:         Default system prompt for the model.
        model_params:          Additional model-specific parameters.
    """

    # --- Required ---
    product_name: str
    model_name: str
    api_endpoint: str

    # --- Model parameters ---
    max_tokens: int = 2048
    temperature: float = 0.7
    timeout: int = 30

    # --- Routing ---
    route_prefix: str = "/local-ai"

    # --- Features ---
    enabled_features: list[str] = field(
        default_factory=lambda: [
            "chat",
            "analysis",
            "summarization",
        ]
    )

    # --- Prompting ---
    system_prompt: str = (
        "You are Semptify AI, a helpful assistant for housing rights and tenant support. "
        "Provide clear, factual information about housing laws, tenant rights, and legal processes. "
        "Do not provide legal advice - refer users to appropriate legal resources when needed."
    )

    # --- Additional parameters ---
    model_params: dict[str, Any] = field(default_factory=dict)

    # --- Supported model presets ---
    MODEL_PRESETS: dict[str, dict[str, Any]] = field(
        default_factory=lambda: {
            "llama-3-8b": {
                "max_tokens": 2048,
                "temperature": 0.7,
                "top_p": 0.9,
            },
            "llama-3-70b": {
                "max_tokens": 4096,
                "temperature": 0.6,
                "top_p": 0.9,
            },
            "mistral-7b": {
                "max_tokens": 2048,
                "temperature": 0.7,
                "top_p": 0.95,
            },
            "gemma-7b": {
                "max_tokens": 2048,
                "temperature": 0.6,
                "top_p": 0.9,
            },
        }
    )

    def get_model_config(self) -> dict[str, Any]:
        """Get complete model configuration with presets applied."""
        preset = self.MODEL_PRESETS.get(self.model_name, {})
        return {
            "model": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "timeout": self.timeout,
            **preset,
            **self.model_params,
        }

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        return feature in self.enabled_features
