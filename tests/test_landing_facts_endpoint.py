"""Tests for the public landing facts endpoint and auto-hide behavior."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.utc import utc_now
from app.main import app
from app.modules.context_engine.models import ContextFact


@pytest.fixture
async def async_client():
    """Create async test client against the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def landing_facts(db_session):
    """Create a verified and an unverified landing fact for filtering tests."""
    now = utc_now().replace(tzinfo=None)
    future = now.replace(year=2099, month=1, day=1)

    verified = ContextFact(
        subject="landing",
        jurisdiction="US",
        claim="More than 80% of landlords have a lawyer in eviction court.",
        source_url="https://example.test/nccrc",
        source_name="Test Source",
        citation="Test citation",
        canonical_value="4% of tenants are represented, compared to 84% of landlords",
        is_verified=True,
        verified_at=now,
        expires_at=future,
        created_at=now,
    )
    unverified = ContextFact(
        subject="landing",
        jurisdiction="US",
        claim="Landlords use AI to set your rent.",
        source_url="https://example.test/rent",
        source_name="Rent Test",
        citation="Rent citation",
        canonical_value=None,
        is_verified=False,
        verified_at=now,
        expires_at=future,
        created_at=now,
    )
    expired = ContextFact(
        subject="landing",
        jurisdiction="US",
        claim="This claim is expired.",
        source_url="https://example.test/expired",
        source_name="Expired",
        is_verified=True,
        verified_at=now,
        expires_at=now,
        created_at=now,
    )

    db_session.add_all([verified, unverified, expired])
    await db_session.commit()
    for f in [verified, unverified, expired]:
        await db_session.refresh(f)
    return {"verified": verified, "unverified": unverified, "expired": expired}


@pytest.mark.anyio
async def test_api_landing_facts_returns_only_verified_non_expired(
    async_client, landing_facts
):
    """GET /api/landing/facts only returns verified, non-expired landing claims."""
    response = await async_client.get("/api/landing/facts")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["claim"] == landing_facts["verified"].claim
    assert data[0]["source_url"] == landing_facts["verified"].source_url


@pytest.mark.anyio
async def test_index_page_renders_without_landing_facts(async_client):
    """The index page renders cleanly when no verified landing facts exist."""
    response = await async_client.get("/")
    assert response.status_code == 200
    assert "Semptify" in response.text
