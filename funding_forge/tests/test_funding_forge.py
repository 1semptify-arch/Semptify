"""Funding Forge API tests."""

import os
import shutil
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./funding_forge_test.db"
os.environ["UPLOADS_DIR"] = "funding_forge_test_uploads"
os.environ["FUNDING_FORGE_KEY"] = ""

import pytest_asyncio  # noqa: E402
from asgi_lifespan import LifespanManager  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from funding_forge.main import app  # noqa: E402


@pytest_asyncio.fixture
async def client():
    """Create an async test client with a fresh test database."""
    Path("funding_forge_test_uploads").mkdir(parents=True, exist_ok=True)
    async with LifespanManager(app) as manager:
        transport = ASGITransport(app=manager.app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as c:
            yield c
    # Cleanup after each test once the engine has been disposed.
    db_path = Path("funding_forge_test.db")
    if db_path.exists():
        db_path.unlink()
    uploads_path = Path("funding_forge_test_uploads")
    if uploads_path.exists():
        shutil.rmtree(uploads_path, ignore_errors=True)


async def test_health(client):
    """The health endpoint returns a healthy status."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["module"] == "funding_forge"


async def test_funder_crud(client):
    """Funders can be created, listed, updated, and deleted."""
    create = await client.post(
        "/api/funders",
        json={
            "name": "Test Funder",
            "type": "foundation",
            "status": "researching",
            "website": "https://example.org",
        },
    )
    assert create.status_code == 201
    funder = create.json()
    assert funder["name"] == "Test Funder"
    assert funder["type"] == "foundation"

    list_response = await client.get("/api/funders")
    assert list_response.status_code == 200
    assert any(f["id"] == funder["id"] for f in list_response.json())

    get_response = await client.get(f"/api/funders/{funder['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Test Funder"

    update = await client.put(
        f"/api/funders/{funder['id']}",
        json={"status": "applied"},
    )
    assert update.status_code == 200
    assert update.json()["status"] == "applied"

    delete = await client.delete(f"/api/funders/{funder['id']}")
    assert delete.status_code == 200
    assert delete.json()["ok"] is True


async def test_seed_suggested_entities(client):
    """The seed endpoint loads suggested funding entities."""
    response = await client.post("/api/seed")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["funders_created"] > 0
    assert data["contacts_created"] > 0

    list_response = await client.get("/api/funders")
    assert list_response.status_code == 200
    assert len(list_response.json()) >= data["funders_created"]
