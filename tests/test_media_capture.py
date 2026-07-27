"""Tests for media capture endpoint."""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.cookie_auth import sign_user_id
from app.main import app


def _auth_client() -> AsyncClient:
    """Return an async test client with a valid signed user cookie."""
    from httpx import ASGITransport

    user_id = "GU7x9kM2pQ"
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    client.cookies.set("semptify_uid", sign_user_id(user_id))
    return client


@pytest.mark.anyio
async def test_media_capture_requires_authentication():
    """Unauthenticated POST /api/media/capture should be rejected."""
    from httpx import ASGITransport

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/media/capture", data={"media_type": "photo"})
    assert response.status_code in (401, 403, 307)


@pytest.mark.anyio
async def test_media_capture_uploads_photo():
    """Authenticated photo upload returns vault_id from vault service."""
    fake_doc = MagicMock()
    fake_doc.vault_id = "doc_test_1234"

    with patch("app.services.vault_upload_service.get_vault_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.upload = AsyncMock(return_value=fake_doc)
        mock_get_service.return_value = mock_service

        async with _auth_client() as client:
            response = await client.post(
                "/api/media/capture",
                data={"media_type": "photo"},
                files={"file": ("photo.jpg", BytesIO(b"fake-image-bytes"), "image/jpeg")},
            )

    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert result["vault_id"] == "doc_test_1234"
    assert result["media_type"] == "photo"


@pytest.mark.anyio
async def test_media_capture_rejects_empty_file():
    """Empty file upload returns 400."""
    async with _auth_client() as client:
        response = await client.post(
            "/api/media/capture",
            data={"media_type": "photo"},
            files={"file": ("empty.jpg", BytesIO(b""), "image/jpeg")},
        )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_media_capture_rejects_invalid_media_type():
    """Invalid media_type returns 400."""
    async with _auth_client() as client:
        response = await client.post(
            "/api/media/capture",
            data={"media_type": "video"},
            files={"file": ("video.mp4", BytesIO(b"fake"), "video/mp4")},
        )
    assert response.status_code == 400
