"""Tests for app.services.groq_ai."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.groq_ai import GroqAIService, GroqAnalysisResult


@pytest.fixture
def no_key_service():
    """Groq service without an API key."""
    with patch("app.services.groq_ai.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(groq_api_key=None)
        yield GroqAIService()


@pytest.fixture
def with_key_service():
    """Groq service with an API key."""
    with patch("app.services.groq_ai.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(groq_api_key="test-key")
        yield GroqAIService()


def test_service_unavailable_without_key(no_key_service):
    """is_available returns False when no API key is configured."""
    assert no_key_service.is_available is False


def test_service_available_with_key(with_key_service):
    """is_available returns True when an API key is configured."""
    assert with_key_service.is_available is True
    assert with_key_service.api_key == "test-key"


@pytest.mark.asyncio
async def test_analyze_document_fallback(no_key_service):
    """analyze_document falls back to rule-based classification when no key."""
    result = await no_key_service.analyze_document("This is an eviction notice", "notice.pdf")
    assert isinstance(result, GroqAnalysisResult)
    assert result.doc_type == "eviction_notice"
    assert result.confidence > 0.5


@pytest.mark.asyncio
async def test_analyze_document_with_api(with_key_service):
    """analyze_document parses a mocked API response."""
    payload = {
        "doc_type": "lease",
        "confidence": 0.9,
        "title": "Lease",
        "summary": "Summary",
        "key_dates": [],
        "key_parties": [],
        "key_amounts": [],
        "key_terms": [],
        "issues_detected": [],
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(payload)}}]
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=AsyncMock(return_value=mock_response)))
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await with_key_service.analyze_document("lease text", "lease.pdf", doc_hint="lease")
    assert isinstance(result, GroqAnalysisResult)
    assert result.doc_type == "lease"
    assert result.confidence == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_analyze_document_api_failure_falls_back(with_key_service):
    """analyze_document falls back when the API call fails."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal error"

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=AsyncMock(return_value=mock_response)))
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await with_key_service.analyze_document("This is a lease agreement", "lease.pdf")
    assert isinstance(result, GroqAnalysisResult)
    assert result.doc_type == "lease"


def test_build_analysis_prompt(with_key_service):
    """_build_analysis_prompt truncates text and adds hint."""
    long_text = "a" * 7000
    prompt = with_key_service._build_analysis_prompt(long_text, "long.pdf", "lease")
    assert "long.pdf" in prompt
    assert "lease" in prompt
    assert "[... document truncated ...]" in prompt


@pytest.mark.asyncio
async def test_call_groq(with_key_service):
    """_call_groq parses a mocked API response."""
    payload = {"doc_type": "other", "confidence": 0.5}
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(payload)}}]
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=AsyncMock(return_value=mock_response)))
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await with_key_service._call_groq("prompt")
    assert result == payload


def test_parse_result(with_key_service):
    """_parse_result builds a GroqAnalysisResult from dict data."""
    data = {
        "doc_type": "repair_request",
        "confidence": "0.8",
        "title": "Repair Request",
        "summary": "Fix the sink",
        "key_dates": [],
        "key_parties": [],
        "key_amounts": [],
        "key_terms": [],
        "issues_detected": [],
    }
    result = with_key_service._parse_result(data)
    assert result.doc_type == "repair_request"
    assert result.confidence == pytest.approx(0.8)


def test_fallback_analysis_keywords(with_key_service):
    """_fallback_analysis classifies text by keywords."""
    for text, expected in (
        ("eviction notice", "eviction_notice"),
        ("summons court date", "court_summons"),
        ("lease agreement", "lease"),
        ("notice to quit vacate", "notice_to_quit"),
        ("rent increase", "rent_increase"),
        ("receipt payment received", "receipt"),
        ("repair maintenance request", "repair_request"),
        ("security deposit itemization", "security_deposit"),
    ):
        result = with_key_service._fallback_analysis(text, "doc.pdf")
        assert result.doc_type == expected


@pytest.mark.asyncio
async def test_quick_classify_fallback(no_key_service):
    """quick_classify returns a fallback tuple when no key."""
    doc_type, confidence = await no_key_service.quick_classify("This is a lease agreement")
    assert doc_type == "lease"
    assert confidence > 0.5


@pytest.mark.asyncio
async def test_quick_classify_with_api(with_key_service):
    """quick_classify returns values from a mocked API response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"doc_type": "receipt", "confidence": 0.8})}}]
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=AsyncMock(return_value=mock_response)))
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

        doc_type, confidence = await with_key_service.quick_classify("paid $100")
    assert doc_type == "receipt"
    assert confidence == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_summarize_for_tenant_fallback(no_key_service):
    """summarize_for_tenant returns a fallback when no key."""
    result = await no_key_service.summarize_for_tenant("text", "eviction")
    assert "unavailable" in result
