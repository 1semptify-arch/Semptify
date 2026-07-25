"""Funding Forge API tests."""

import os
import shutil
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./funding_forge_test.db"
os.environ["UPLOADS_DIR"] = "funding_forge_test_uploads"
os.environ["FUNDING_FORGE_STORAGE_BACKEND"] = "local"
os.environ["FUNDING_FORGE_ADMIN_USERNAME"] = "admin"
os.environ["FUNDING_FORGE_ADMIN_PASSWORD"] = "test-password"  # pragma: allowlist secret

import pytest_asyncio  # noqa: E402
from asgi_lifespan import LifespanManager  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from funding_forge.auth import create_admin_token  # noqa: E402
from funding_forge.main import app  # noqa: E402


def admin_headers() -> dict[str, str]:
    """Return headers that authenticate as the configured test admin."""
    return {"x-admin-token": create_admin_token()}


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
    """The health endpoint returns a healthy status without authentication."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["module"] == "funding_forge"


async def test_api_requires_admin(client):
    """API endpoints reject unauthenticated requests."""
    response = await client.get("/api/funders")
    assert response.status_code == 401


async def test_admin_login_and_crud(client):
    """Admin login works and funders can be managed."""
    headers = admin_headers()

    create = await client.post(
        "/api/funders",
        headers=headers,
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

    list_response = await client.get("/api/funders", headers=headers)
    assert list_response.status_code == 200
    assert any(f["id"] == funder["id"] for f in list_response.json())

    get_response = await client.get(f"/api/funders/{funder['id']}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Test Funder"

    update = await client.put(
        f"/api/funders/{funder['id']}",
        headers=headers,
        json={"status": "applied"},
    )
    assert update.status_code == 200
    assert update.json()["status"] == "applied"

    delete = await client.delete(f"/api/funders/{funder['id']}", headers=headers)
    assert delete.status_code == 200
    assert delete.json()["ok"] is True


async def test_seed_suggested_entities(client):
    """The seed endpoint loads suggested funding entities."""
    headers = admin_headers()
    response = await client.post("/api/seed", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["funders_created"] > 0
    assert data["contacts_created"] > 0

    list_response = await client.get("/api/funders", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) >= data["funders_created"]


async def test_document_upload_and_download(client):
    """Documents can be uploaded, downloaded, and deleted."""
    headers = admin_headers()
    seed = await client.post("/api/seed", headers=headers)
    assert seed.status_code == 200
    funder = await client.get("/api/funders", headers=headers)
    assert funder.status_code == 200
    funder_id = funder.json()[0]["id"]

    opportunity = await client.post(
        "/api/opportunities",
        headers=headers,
        json={
            "funder_id": funder_id,
            "title": "Test opportunity",
            "opportunity_type": "grant",
        },
    )
    assert opportunity.status_code == 201
    opportunity_id = opportunity.json()["id"]

    upload = await client.post(
        "/api/documents",
        headers=headers,
        data={"opportunity_id": str(opportunity_id), "description": "test file"},
        files={"file": ("hello.txt", b"hello world", "text/plain")},
    )
    assert upload.status_code == 201
    document = upload.json()
    assert document["storage_type"] == "local"
    assert document["file_size"] == 11

    download = await client.get(f"/api/documents/{document['id']}", headers=headers)
    assert download.status_code == 200
    assert download.content == b"hello world"
    assert download.headers["content-disposition"].startswith('attachment; filename="hello.txt"')

    delete = await client.delete(f"/api/documents/{document['id']}", headers=headers)
    assert delete.status_code == 200
    assert delete.json()["ok"] is True


async def test_email_create_and_send_without_provider(client):
    """Emails are saved and returned; without a provider they remain drafts."""
    headers = admin_headers()
    contact = await client.post(
        "/api/contacts",
        headers=headers,
        json={"name": "Email Contact", "email": "contact@example.org"},
    )
    assert contact.status_code == 201
    contact_id = contact.json()["id"]

    send = await client.post(
        "/api/emails",
        headers=headers,
        json={
            "contact_id": contact_id,
            "to_address": "contact@example.org",
            "subject": "Hello",
            "body": "This is a test email.",
        },
    )
    assert send.status_code == 201
    email = send.json()
    assert email["to_address"] == "contact@example.org"
    assert email["subject"] == "Hello"
    assert email["status"] == "draft"
    assert email["provider"] == "none"

    get = await client.get(f"/api/emails/{email['id']}", headers=headers)
    assert get.status_code == 200
    assert get.json()["id"] == email["id"]

    list_response = await client.get("/api/emails", headers=headers)
    assert list_response.status_code == 200
    assert any(e["id"] == email["id"] for e in list_response.json())

    delete = await client.delete(f"/api/emails/{email['id']}", headers=headers)
    assert delete.status_code == 200
    assert delete.json()["ok"] is True
