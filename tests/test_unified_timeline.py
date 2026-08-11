"""Tests for eviction_timeline integration into the unified timeline."""

from datetime import timedelta
from uuid import uuid4

import pytest

from app.core.database import get_db_session
from app.core.utc import utc_now
from app.models.models import EvictionTimelineEvent


@pytest.mark.anyio
async def test_eviction_timeline_in_unified_timeline(authenticated_client):
    """An EvictionTimelineEvent appears in the unified timeline with correct mapping."""
    user_id = "GUa1b2c3d4"  # matches authenticated_client fixture
    event = EvictionTimelineEvent(
        id=str(uuid4()),
        user_id=user_id,
        event_type="court_filing",
        event_date=utc_now() - timedelta(days=10),
        source="court",
        source_document_id="doc-123",
        content_overlay_id="overlay-456",
        jurisdiction="MN",
    )
    async with get_db_session() as db:
        db.add(event)

    response = await authenticated_client.post(
        "/api/timeline/unified",
        json={"item_types": ["timeline_event"]},
    )
    assert response.status_code == 200
    data = response.json()
    items = [i for i in data["items"] if i["item_subtype"] == "court_filing"]
    assert len(items) == 1

    item = items[0]
    assert item["item_type"] == "timeline_event"
    assert item["title"] == "Court Filing"
    assert item["item_subtype"] == "court_filing"
    assert item["source"] == "upload"
    assert item["is_evidence"] is True
    assert item["is_deadline"] is False
    assert item["urgency"] == "normal"
    assert item["document_id"] == "doc-123"
    assert item["overlay_id"] == "overlay-456"
    assert item["metadata"]["jurisdiction"] == "MN"
    assert item["metadata"]["content_overlay_id"] == "overlay-456"


@pytest.mark.anyio
async def test_eviction_timeline_deadline_and_manual_source(authenticated_client):
    """Deadline keyword and manual source are mapped correctly."""
    user_id = "GUa1b2c3d4"
    event = EvictionTimelineEvent(
        id=str(uuid4()),
        user_id=user_id,
        event_type="response_deadline",
        event_date=utc_now() - timedelta(days=5),
        source="manual",
        subject_id="sub-789",
    )
    async with get_db_session() as db:
        db.add(event)

    response = await authenticated_client.post(
        "/api/timeline/unified",
        json={"item_types": ["timeline_event"]},
    )
    assert response.status_code == 200
    data = response.json()
    items = [i for i in data["items"] if i["item_subtype"] == "response_deadline"]
    assert len(items) == 1

    item = items[0]
    assert item["title"] == "Response Deadline"
    assert item["source"] == "manual"
    assert item["is_evidence"] is False
    assert item["is_deadline"] is True
    assert item["urgency"] == "high"
    assert item["metadata"]["subject_id"] == "sub-789"


@pytest.mark.anyio
async def test_eviction_timeline_evidence_filter(authenticated_client):
    """Evidence-only filter excludes non-eviction-keyword eviction events."""
    user_id = "GUa1b2c3d4"
    evidence = EvictionTimelineEvent(
        id=str(uuid4()),
        user_id=user_id,
        event_type="judgment",
        event_date=utc_now() - timedelta(days=2),
        source="document",
    )
    non_evidence = EvictionTimelineEvent(
        id=str(uuid4()),
        user_id=user_id,
        event_type="payment_plan",
        event_date=utc_now() - timedelta(days=1),
        source="manual",
    )
    async with get_db_session() as db:
        db.add(evidence)
        db.add(non_evidence)

    response = await authenticated_client.post(
        "/api/timeline/unified",
        json={"item_types": ["timeline_event"], "evidence_only": True},
    )
    assert response.status_code == 200
    data = response.json()
    subtypes = {i["item_subtype"] for i in data["items"]}
    assert "judgment" in subtypes
    assert "payment_plan" not in subtypes


@pytest.mark.anyio
async def test_tenant_timeline_renders_eviction_event(authenticated_client):
    """/tenant/timeline (UI Composer) renders an eviction-sourced event."""
    user_id = "GUa1b2c3d4"
    event = EvictionTimelineEvent(
        id=str(uuid4()),
        user_id=user_id,
        event_type="court_filing",
        event_date=utc_now() - timedelta(days=10),
        source="court",
        source_document_id="doc-123",
    )
    async with get_db_session() as db:
        db.add(event)

    response = await authenticated_client.get("/tenant/timeline")
    assert response.status_code == 200
    text = response.text
    assert "Court Filing" in text
    assert "▸" in text
    assert "Evidence" in text


@pytest.mark.anyio
async def test_legacy_timeline_page_loads_with_eviction_event(authenticated_client):
    """/timeline (legacy list page) loads and contains the unified timeline script."""
    user_id = "GUa1b2c3d4"
    event = EvictionTimelineEvent(
        id=str(uuid4()),
        user_id=user_id,
        event_type="response_deadline",
        event_date=utc_now() - timedelta(days=5),
        source="manual",
    )
    async with get_db_session() as db:
        db.add(event)

    response = await authenticated_client.get("/timeline")
    assert response.status_code == 200
    text = response.text
    assert "Timeline" in text
    assert "typeIcon" in text
    assert "is_deadline" in text or "is_evidence" in text
