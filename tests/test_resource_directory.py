"""Tests for the resource directory module."""

import io
from datetime import datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.utc import utc_now
from app.main import app
from app.models.models import Resource


def _client() -> AsyncClient:
    """Return an async test client."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.anyio
async def test_list_resources_empty():
    """Public resource list returns empty by default."""
    async with _client() as client:
        response = await client.get("/api/resources")
    assert response.status_code == 200
    data = response.json()
    assert data["resources"] == []
    assert data["total"] == 0


@pytest.mark.anyio
async def test_create_and_get_resource():
    """Admin create and public read round-trip."""
    payload = {
        "name": "HOME Line MN",
        "category": "legal_aid",
        "service_area": "Minnesota",
        "languages": ["en", "es", "so"],
        "contact_info": {"phone": "612-728-5767", "website": "https://homelinemn.org"},
        "source": "manual",
    }

    async with _client() as client:
        create_resp = await client.post("/admin/resources", json=payload)
        assert create_resp.status_code == 201
        created = create_resp.json()
        resource_id = created["id"]

        get_resp = await client.get(f"/api/resources/{resource_id}")
        assert get_resp.status_code == 200
        fetched = get_resp.json()
        assert fetched["name"] == "HOME Line MN"
        assert fetched["category"] == "legal_aid"
        assert fetched["languages"] == ["en", "es", "so"]
        assert fetched["contact_info"]["phone"] == "612-728-5767"


@pytest.mark.anyio
async def test_list_resources_filter_by_category():
    """Resource list can be filtered by category."""
    async with _client() as client:
        await client.post(
            "/admin/resources",
            json={
                "name": "Tenants Union",
                "category": "tenant_union",
                "service_area": "Hennepin County, MN",
            },
        )
        await client.post(
            "/admin/resources",
            json={
                "name": "Legal Aid",
                "category": "legal_aid",
                "service_area": "Hennepin County, MN",
            },
        )

        response = await client.get("/api/resources?category=legal_aid")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["resources"][0]["name"] == "Legal Aid"


@pytest.mark.anyio
async def test_import_resources_csv():
    """Admin CSV import creates resources and reports counts."""
    csv_text = (
        "name,category,service_area,languages,phone,email,website,source\n"
        "Mid-Minnesota Legal Aid,legal_aid,Minnesota,en;es,651-000-0000,,https://mylegalaid.org,state_source\n"
        "Emergency Shelter Hotline,emergency_shelter,Minneapolis,en,612-111-1111,,,city_source\n"
    )

    async with _client() as client:
        response = await client.post(
            "/admin/resources/import",
            files={"file": ("resources.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["imported"] == 2
    assert data["updated"] == 0
    assert data["skipped"] == 0


@pytest.mark.anyio
async def test_import_csv_rejects_non_csv():
    """Uploading a non-CSV file returns 400."""
    async with _client() as client:
        response = await client.post(
            "/admin/resources/import",
            files={"file": ("resources.txt", io.BytesIO(b"not a csv"), "text/plain")},
        )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_staleness_tracking():
    """Stale resources are surfaced on the stale endpoint."""
    stale_date = (utc_now() - timedelta(days=400)).isoformat()
    fresh_date = (utc_now() - timedelta(days=30)).isoformat()

    async with _client() as client:
        await client.post(
            "/admin/resources",
            json={
                "name": "Old Resource",
                "category": "legal_aid",
                "service_area": "Minnesota",
                "last_verified": stale_date,
            },
        )
        await client.post(
            "/admin/resources",
            json={
                "name": "Fresh Resource",
                "category": "legal_aid",
                "service_area": "Minnesota",
                "last_verified": fresh_date,
            },
        )

        response = await client.get("/admin/resources/stale")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["resources"][0]["name"] == "Old Resource"


@pytest.mark.anyio
async def test_admin_endpoint_blocks_non_admin_network():
    """Admin endpoints return 404 from a non-admin IP."""
    async with _client() as client:
        response = await client.post(
            "/admin/resources",
            json={"name": "Blocked", "category": "legal_aid"},
            headers={"X-Forwarded-For": "8.8.8.8"},
        )
    assert response.status_code == 404
