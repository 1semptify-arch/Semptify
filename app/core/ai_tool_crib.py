"""
Semptify AI Tool Crib - In-house AI Service Management
Version: 1.0.0
Purpose: Centralized management of all AI services and tools
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel

from app.core.utc import utc_now

logger = logging.getLogger(__name__)


class AIServiceType(str, Enum):
    """Types of AI services in the crib."""
    DOCUMENT_CLASSIFIER = "document_classifier"
    LEGAL_ANALYZER = "legal_analyzer"
    TIMELINE_EXTRACTOR = "timeline_extractor"
    EMOTION_DETECTOR = "emotion_detector"
    DUPLICATE_DETECTOR = "duplicate_detector"
    SUMMARIZER = "summarizer"
    TRANSLATOR = "translator"
    OCR_ENGINE = "ocr_engine"


class AIProvider(str, Enum):
    """AI service providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL_LLM = "local_llm"
    SWE_1_6 = "swe_1_6"
    AZURE_AI = "azure_ai"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class AIServiceConfig(BaseModel):
    """Configuration for an AI service."""
    service_type: AIServiceType
    provider: AIProvider
    enabled: bool = True
    api_key_env: str | None = None
    model_name: str | None = None
    max_tokens: int = 4000
    temperature: float = 0.1
    timeout_seconds: int = 30
    retry_attempts: int = 3
    cost_per_request: float = 0.0
    rate_limit_per_minute: int = 60


class AIServiceMetrics(BaseModel):
    """Metrics for an AI service."""
    service_type: AIServiceType
    provider: AIProvider
    requests_total: int = 0
    requests_successful: int = 0
    requests_failed: int = 0
    average_response_time: float = 0.0
    total_cost: float = 0.0
    last_used: datetime | None = None
    error_rate: float = 0.0


class AIToolCrib:
    """Central management of all AI services."""

    def __init__(self):
        self.services: dict[AIServiceType, AIServiceConfig] = {}
        self.metrics: dict[AIServiceType, AIServiceMetrics] = {}
        self._initialize_default_services()

    def _initialize_default_services(self):
        """Initialize default AI service configurations."""
        default_configs = {
            AIServiceType.DOCUMENT_CLASSIFIER: AIServiceConfig(
                service_type=AIServiceType.DOCUMENT_CLASSIFIER,
                provider=AIProvider.SWE_1_6,
                model_name="claude-3-sonnet",
                api_key_env="SWE16_API_KEY",
                cost_per_request=0.003,
            ),
            AIServiceType.LEGAL_ANALYZER: AIServiceConfig(
                service_type=AIServiceType.LEGAL_ANALYZER,
                provider=AIProvider.LOCAL_LLM,
                model_name="legal-llm-v1",
                cost_per_request=0.0,
            ),
            AIServiceType.TIMELINE_EXTRACTOR: AIServiceConfig(
                service_type=AIServiceType.TIMELINE_EXTRACTOR,
                provider=AIProvider.OPENAI,
                model_name="gpt-4-turbo",
                api_key_env="OPENAI_API_KEY",
                cost_per_request=0.01,
            ),
            AIServiceType.EMOTION_DETECTOR: AIServiceConfig(
                service_type=AIServiceType.EMOTION_DETECTOR,
                provider=AIProvider.ANTHROPIC,
                model_name="claude-3-haiku",
                api_key_env="ANTHROPIC_API_KEY",
                cost_per_request=0.001,
            ),
            AIServiceType.DUPLICATE_DETECTOR: AIServiceConfig(
                service_type=AIServiceType.DUPLICATE_DETECTOR,
                provider=AIProvider.LOCAL_LLM,
                model_name="similarity-model",
                cost_per_request=0.0,
            ),
            AIServiceType.SUMMARIZER: AIServiceConfig(
                service_type=AIServiceType.SUMMARIZER,
                provider=AIProvider.GEMINI,
                model_name="gemini-pro",
                api_key_env="GEMINI_API_KEY",
                cost_per_request=0.002,
            ),
            AIServiceType.OCR_ENGINE: AIServiceConfig(
                service_type=AIServiceType.OCR_ENGINE,
                provider=AIProvider.AZURE_AI,
                model_name="azure-ocr-v4",
                api_key_env="AZURE_AI_KEY",
                cost_per_request=0.001,
            ),
        }

        for service_type, config in default_configs.items():
            self.services[service_type] = config
            self.metrics[service_type] = AIServiceMetrics(
                service_type=service_type,
                provider=config.provider
            )

    def get_service(self, service_type: AIServiceType) -> AIServiceConfig | None:
        """Get configuration for an AI service."""
        return self.services.get(service_type)

    def enable_service(self, service_type: AIServiceType):
        """Enable an AI service."""
        if service_type in self.services:
            self.services[service_type].enabled = True
            logger.info(f"Enabled AI service: {service_type}")

    def disable_service(self, service_type: AIServiceType):
        """Disable an AI service."""
        if service_type in self.services:
            self.services[service_type].enabled = False
            logger.info(f"Disabled AI service: {service_type}")

    def update_metrics(self, service_type: AIServiceType, success: bool,
                      response_time: float, cost: float = 0.0):
        """Update metrics for an AI service."""
        if service_type not in self.metrics:
            return

        metrics = self.metrics[service_type]
        metrics.requests_total += 1
        metrics.last_used = utc_now()

        if success:
            metrics.requests_successful += 1
        else:
            metrics.requests_failed += 1

        # Update average response time
        total_time = metrics.average_response_time * (metrics.requests_total - 1) + response_time
        metrics.average_response_time = total_time / metrics.requests_total

        # Update cost
        metrics.total_cost += cost

        # Calculate error rate
        metrics.error_rate = metrics.requests_failed / metrics.requests_total if metrics.requests_total > 0 else 0

    def get_metrics(self, service_type: AIServiceType | None = None) -> dict[str, AIServiceMetrics]:
        """Get metrics for AI services."""
        if service_type:
            return {service_type.value: self.metrics.get(service_type)}
        return {k.value: v for k, v in self.metrics.items()}

    def get_health_status(self) -> dict[str, Any]:
        """Get health status of all AI services."""
        status = {
            "total_services": len(self.services),
            "enabled_services": sum(1 for s in self.services.values() if s.enabled),
            "services": {}
        }

        for service_type, config in self.services.items():
            metrics = self.metrics.get(service_type)
            status["services"][service_type.value] = {
                "enabled": config.enabled,
                "provider": config.provider.value,
                "model": config.model_name,
                "health": "healthy" if metrics and metrics.error_rate < 0.1 else "degraded",
                "error_rate": metrics.error_rate if metrics else 0,
                "avg_response_time": metrics.average_response_time if metrics else 0,
                "last_used": metrics.last_used.isoformat() if metrics and metrics.last_used else None,
            }

        return status

    def get_cost_report(self, start_date: datetime | None = None) -> dict[str, float]:
        """Get cost report for AI services."""
        # This would typically query a database for historical metrics
        # For now, return current total costs
        return {
            service_type.value: metrics.total_cost
            for service_type, metrics in self.metrics.items()
        }


# Global instance
ai_tool_crib = AIToolCrib()


# Service wrappers for easy access
def classify_document(content: str, filename: str) -> str:
    """Classify a document using the configured AI service."""
    config = ai_tool_crib.get_service(AIServiceType.DOCUMENT_CLASSIFIER)
    if not config or not config.enabled:
        return "unknown"

    # Implementation would call the actual AI service
    # For now, return placeholder
    return "unknown"


def analyze_legal_content(content: str) -> dict[str, Any]:
    """Analyze legal content using the configured AI service."""
    config = ai_tool_crib.get_service(AIServiceType.LEGAL_ANALYZER)
    if not config or not config.enabled:
        return {"analysis": "Service not available"}

    # Implementation would call the actual AI service
    return {"analysis": "Legal analysis complete"}


def extract_timeline(content: str) -> list[dict[str, Any]]:
    """Extract timeline events from content."""
    config = ai_tool_crib.get_service(AIServiceType.TIMELINE_EXTRACTOR)
    if not config or not config.enabled:
        return []

    # Implementation would call the actual AI service
    return []


def detect_emotion(content: str) -> dict[str, float]:
    """Detect emotion in content."""
    config = ai_tool_crib.get_service(AIServiceType.EMOTION_DETECTOR)
    if not config or not config.enabled:
        return {}

    # Implementation would call the actual AI service
    return {}
