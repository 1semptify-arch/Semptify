"""Tests for app.services.gemini_ai."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.gemini_ai import GeminiAIService, GeminiAnalysisResult


@pytest.fixture
def no_key_service():
    """Gemini service without an API key."""
    with patch("app.services.gemini_ai.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(gemini_api_key=None, google_ai_api_key=None)
        yield GeminiAIService()


@pytest.fixture
def with_key_service():
    """Gemini service with an API key."""
    with patch("app.services.gemini_ai.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(gemini_api_key="test-key", google_ai_api_key=None, gemini_model=None)
        yield GeminiAIService()


def test_service_unavailable_without_key(no_key_service):
    """is_available returns False when no API key is configured."""
    assert no_key_service.is_available is False


def test_service_available_with_key(with_key_service):
    """is_available returns True when an API key is configured."""
    assert with_key_service.is_available is True
    assert with_key_service.api_key == "test-key"


@pytest.mark.asyncio
async def test_analyze_document_raises_when_unavailable(no_key_service):
    """analyze_document raises if no API key is present."""
    with pytest.raises(ValueError):
        await no_key_service.analyze_document("some text", "file.pdf")


@pytest.mark.asyncio
async def test_analyze_document_success(with_key_service):
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
        "candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=AsyncMock(return_value=mock_response)))
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await with_key_service.analyze_document("lease text", "lease.pdf", doc_hint="lease")
    assert isinstance(result, GeminiAnalysisResult)
    assert result.doc_type == "lease"
    assert result.confidence == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_chat_success(with_key_service):
    """chat returns text from a mocked API response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "A helpful response"}]}}]
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=AsyncMock(return_value=mock_response)))
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

        response = await with_key_service.chat("What are my rights?")
    assert response == "A helpful response"


@pytest.mark.asyncio
async def test_generate_document_success(with_key_service):
    """generate_document returns text from a mocked API response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Generated document"}]}}]
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=AsyncMock(return_value=mock_response)))
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

        response = await with_key_service.generate_document("answer", {"tenant": "Jane"})
    assert response == "Generated document"


def test_build_analysis_prompt(with_key_service):
    """_build_analysis_prompt includes the hint and document text."""
    prompt = with_key_service._build_analysis_prompt("document body", "lease.pdf", "lease")
    assert "lease.pdf" in prompt
    assert "lease" in prompt
    assert "document body" in prompt
    assert "JSON" in prompt


def test_parse_response_markdown_json(with_key_service):
    """_parse_response cleans markdown fences and parses JSON."""
    payload = {
        "doc_type": "notice",
        "confidence": 0.75,
        "title": "Notice",
        "summary": "Summary",
        "key_dates": [],
        "key_parties": [],
        "key_amounts": [],
        "key_terms": [],
        "issues_detected": [],
    }
    wrapped = f"```json\n{json.dumps(payload)}\n```"
    result = with_key_service._parse_response(wrapped)
    assert result.doc_type == "notice"
    assert result.confidence == pytest.approx(0.75)
