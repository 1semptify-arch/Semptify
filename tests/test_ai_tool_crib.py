"""Tests for app.core.ai_tool_crib."""

import pytest

from app.core.ai_tool_crib import (
    AIProvider,
    AIServiceType,
    AIToolCrib,
    ai_tool_crib,
    analyze_legal_content,
    classify_document,
    detect_emotion,
    extract_timeline,
)


def test_default_services_initialized():
    """AIToolCrib initializes the default set of services."""
    crib = AIToolCrib()
    assert AIServiceType.DOCUMENT_CLASSIFIER in crib.services
    assert AIServiceType.LEGAL_ANALYZER in crib.services
    assert AIServiceType.OCR_ENGINE in crib.services


def test_get_service_found():
    """get_service returns a known service config."""
    crib = AIToolCrib()
    config = crib.get_service(AIServiceType.DOCUMENT_CLASSIFIER)
    assert config is not None
    assert config.service_type == AIServiceType.DOCUMENT_CLASSIFIER


def test_get_service_missing():
    """get_service returns None for a service that was removed."""
    crib = AIToolCrib()
    assert crib.get_service("not_a_service") is None  # type: ignore[arg-type]


def test_enable_disable_service():
    """enable_service and disable_service toggle the enabled flag."""
    crib = AIToolCrib()
    crib.disable_service(AIServiceType.DOCUMENT_CLASSIFIER)
    assert crib.services[AIServiceType.DOCUMENT_CLASSIFIER].enabled is False

    crib.enable_service(AIServiceType.DOCUMENT_CLASSIFIER)
    assert crib.services[AIServiceType.DOCUMENT_CLASSIFIER].enabled is True


def test_enable_disable_unknown_service_does_not_raise():
    """Toggling an unknown service logs and returns without error."""
    crib = AIToolCrib()
    crib.disable_service("unknown")  # type: ignore[arg-type]


def test_update_metrics_success_and_failure():
    """update_metrics tracks requests, successes, failures, and cost."""
    crib = AIToolCrib()
    crib.update_metrics(AIServiceType.DOCUMENT_CLASSIFIER, success=True, response_time=1.0, cost=0.01)
    crib.update_metrics(AIServiceType.DOCUMENT_CLASSIFIER, success=False, response_time=0.5, cost=0.0)

    metrics = crib.metrics[AIServiceType.DOCUMENT_CLASSIFIER]
    assert metrics.requests_total == 2
    assert metrics.requests_successful == 1
    assert metrics.requests_failed == 1
    assert metrics.total_cost == pytest.approx(0.01)
    assert metrics.error_rate == pytest.approx(0.5)


def test_update_metrics_unknown_service():
    """update_metrics is a no-op for an unknown service."""
    crib = AIToolCrib()
    crib.update_metrics("unknown", success=True, response_time=1.0)  # type: ignore[arg-type]


def test_get_metrics():
    """get_metrics returns metrics by service value."""
    crib = AIToolCrib()
    crib.update_metrics(AIServiceType.LEGAL_ANALYZER, success=True, response_time=0.2)
    metrics = crib.get_metrics(AIServiceType.LEGAL_ANALYZER)
    assert AIServiceType.LEGAL_ANALYZER.value in metrics
    assert metrics[AIServiceType.LEGAL_ANALYZER.value] is not None


def test_get_all_metrics():
    """get_metrics with no argument returns all metrics."""
    crib = AIToolCrib()
    all_metrics = crib.get_metrics()
    assert AIServiceType.DOCUMENT_CLASSIFIER.value in all_metrics


def test_get_health_status():
    """get_health_status reports on all services."""
    crib = AIToolCrib()
    status = crib.get_health_status()
    assert status["total_services"] == len(crib.services)
    assert "services" in status
    assert AIServiceType.DOCUMENT_CLASSIFIER.value in status["services"]


def test_get_cost_report():
    """get_cost_report returns total costs per service."""
    crib = AIToolCrib()
    crib.update_metrics(AIServiceType.SUMMARIZER, success=True, response_time=0.5, cost=0.05)
    report = crib.get_cost_report()
    assert report[AIServiceType.SUMMARIZER.value] == pytest.approx(0.05)


def test_global_ai_tool_crib_available():
    """The module-level ai_tool_crib global is an AIToolCrib instance."""
    assert isinstance(ai_tool_crib, AIToolCrib)


def test_wrapper_functions():
    """High-level wrapper functions return defaults without real AI calls."""
    assert classify_document("some text", "lease.pdf") == "unknown"
    assert isinstance(analyze_legal_content("some text"), dict)
    assert extract_timeline("some text") == []
    assert detect_emotion("some text") == {}
