"""Tests for the Context Engine content-level verifier (Phase B)."""

import pytest

from app.core.utc import utc_now
from app.modules.context_engine.models import ContextFact
from app.modules.context_engine.verifier import _normalize, verify_fact


class _MockResponse:
    """Minimal httpx.Response-like object for monkeypatching _fetch_source."""

    def __init__(self, status_code: int, text: str, content_type: str = "text/html"):
        self.status_code = status_code
        self.text = text
        self.content = text.encode("utf-8")
        self.headers = {"content-type": content_type}


def _mock_fetch(html: str, status: int = 200):
    """Return an async function that mimics _fetch_source."""

    async def _fetch(url: str) -> _MockResponse:
        return _MockResponse(status, html)

    return _fetch


@pytest.fixture
async def landing_fact(db_session):
    """Create a landing ContextFact for testing."""
    now = utc_now().replace(tzinfo=None)
    fact = ContextFact(
        subject="landing",
        jurisdiction="US",
        claim="More than 80% of landlords have a lawyer in eviction court.",
        source_url="https://example.test/nccrc",
        source_name="Test Source",
        citation="Test citation",
        canonical_value="4% of tenants are represented, compared to 84% of landlords",
        extraction_pattern=r"\d+% of tenants are represented, compared to \d+% of landlords",
        is_verified=True,
        verified_at=now,
        expires_at=now.replace(year=2099, month=1, day=1),
        created_at=now,
    )
    db_session.add(fact)
    await db_session.commit()
    await db_session.refresh(fact)
    return fact


@pytest.mark.anyio
async def test_verify_fact_content_matches(landing_fact, monkeypatch):
    """Verifier returns True when extracted content matches canonical_value."""
    html = (
        "<p>only 4% of tenants are represented, compared to 84% of landlords</p>"
    )
    monkeypatch.setattr(
        "app.modules.context_engine.verifier._fetch_source",
        _mock_fetch(html),
    )

    ok = await verify_fact(landing_fact)
    assert ok is True


@pytest.mark.anyio
async def test_verify_fact_content_mismatch(landing_fact, monkeypatch):
    """Verifier returns False and raises an alert when the source figure drifts."""
    html = (
        "<p>only 5% of tenants are represented, compared to 83% of landlords</p>"
    )
    monkeypatch.setattr(
        "app.modules.context_engine.verifier._fetch_source",
        _mock_fetch(html),
    )

    ok = await verify_fact(landing_fact)
    assert ok is False


@pytest.mark.anyio
async def test_verify_fact_extraction_fails(landing_fact, monkeypatch):
    """Verifier returns False when the extraction pattern no longer matches."""
    html = "<p>Some unrelated content with no representation rates.</p>"
    monkeypatch.setattr(
        "app.modules.context_engine.verifier._fetch_source",
        _mock_fetch(html),
    )

    ok = await verify_fact(landing_fact)
    assert ok is False


@pytest.mark.anyio
async def test_verify_fact_source_unavailable(landing_fact, monkeypatch):
    """Verifier returns False when the source URL returns a 4xx/5xx."""
    monkeypatch.setattr(
        "app.modules.context_engine.verifier._fetch_source",
        _mock_fetch("", status=404),
    )

    ok = await verify_fact(landing_fact)
    assert ok is False


@pytest.mark.anyio
async def test_verify_fact_unset_canonical_value(landing_fact, db_session, monkeypatch):
    """When canonical_value is None, extraction reports the value but stays unverified."""
    landing_fact.canonical_value = None
    landing_fact.extraction_pattern = r"\$\d+ per month per unit"
    await db_session.commit()
    html = "<p>Algorithmic pricing added $53 per month per unit.</p>"
    monkeypatch.setattr(
        "app.modules.context_engine.verifier._fetch_source",
        _mock_fetch(html),
    )

    ok = await verify_fact(landing_fact)
    assert ok is False


def test_normalize_collapses_whitespace():
    """Whitespace normalization is stable across line breaks and multiple spaces."""
    raw = "  4%   of  tenants \n are  represented  "
    assert _normalize(raw) == "4% of tenants are represented"
