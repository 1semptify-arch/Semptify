"""Tests for the Document Color Key + footnote annotation endpoints.

Covers GET/PUT /api/unified-overlays/annotations/color-key and
POST /api/unified-overlays/annotations/footnote with a fake overlay
manager — storage I/O is out of scope (it needs live OAuth).
"""

from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

import importlib

# The package __init__ rebinds `.router` to the APIRouter — use importlib
# to get the actual module object for monkeypatching.
uo_router = importlib.import_module("app.modules.unified_overlays.router")
from app.core.database import get_db
from app.core.config import get_settings
from app.core.overlay_types import OverlayType
from app.core.security import yellow_access
from app.core.user_context import UserContext, UserRole, StorageProvider
from app.models.unified_overlay_models import (
    CreateOverlayResponse,
    GetOverlaysResponse,
    UnifiedOverlay,
)


class FakeManager:
    """In-memory stand-in for UnifiedOverlayManager."""

    def __init__(self):
        self.store = {}
        self.created_requests = []

    async def get_overlays(self, document_id=None, overlay_type=None, created_by=None, **kw):
        overlays = [
            ov for ov in self.store.values()
            if (document_id is None or ov.document_id == document_id)
            and (overlay_type is None or ov.overlay_type == overlay_type)
            and (created_by is None or ov.created_by == created_by)
        ]
        return GetOverlaysResponse(success=True, overlays=overlays, count=len(overlays))

    async def create_overlay(self, request):
        ov = UnifiedOverlay(
            overlay_type=request.overlay_type,
            document_id=request.document_id,
            vault_path=request.vault_path,
            payload=request.payload,
            created_by="GUtestuser1",
        )
        self.store[ov.overlay_id] = ov
        self.created_requests.append(request)
        return CreateOverlayResponse(
            success=True,
            overlay_id=ov.overlay_id,
            overlay_type=ov.overlay_type,
            message="created",
        )

    async def update_overlay(self, overlay_id, payload=None, metadata=None):
        ov = self.store.get(overlay_id)
        if not ov:
            return False
        if payload is not None:
            ov.payload = payload
        if metadata is not None:
            ov.metadata = metadata
        return True


@pytest.fixture()
def client(monkeypatch):
    manager = FakeManager()

    async def fake_storage(user, db, settings):
        return object()

    async def fake_manager(storage, user_id):
        return manager

    monkeypatch.setattr(uo_router, "get_storage_client", fake_storage)
    monkeypatch.setattr(uo_router, "get_unified_overlay_manager", fake_manager)

    app = FastAPI()
    app.include_router(uo_router.router)

    def fake_user():
        return UserContext(
            user_id="GUtestuser1",
            provider=StorageProvider.GOOGLE_DRIVE,
            storage_user_id="x",
            access_token="tok",
            role=UserRole.TENANT,
        )

    app.dependency_overrides[yellow_access] = fake_user
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace()

    with TestClient(app) as c:
        c.fake_manager = manager
        yield c


def test_color_key_default_palette(client):
    r = client.get("/api/unified-overlays/annotations/color-key", params={"document_id": "doc-1"})
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["is_default"] is True
    assert data["overlay_id"] is None
    assert set(data["colors"]) == {"yellow", "red", "blue", "green", "orange", "purple"}


def test_color_key_put_creates_then_get_returns_stored(client):
    r = client.put(
        "/api/unified-overlays/annotations/color-key",
        params={"document_id": "doc-1", "vault_path": "vault/doc-1"},
        json={"colors": {"red": "contradiction between signed and unsigned", "magenta": "not allowed"}},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["updated"] is False
    # Unknown colors are dropped
    assert "magenta" not in data["colors"]
    assert data["colors"]["red"] == "contradiction between signed and unsigned"

    # Stored overlay is a DOCUMENT_KEY for the right document
    req = client.fake_manager.created_requests[-1]
    assert req.overlay_type == OverlayType.DOCUMENT_KEY
    assert req.document_id == "doc-1"

    # GET now returns the stored meanings merged over defaults
    r2 = client.get("/api/unified-overlays/annotations/color-key", params={"document_id": "doc-1"})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["is_default"] is False
    assert d2["overlay_id"] == data["overlay_id"]
    assert d2["colors"]["red"] == "contradiction between signed and unsigned"
    assert "yellow" in d2["colors"]  # defaults still fill unset colors


def test_color_key_put_updates_existing_overlay(client):
    put = lambda colors: client.put(
        "/api/unified-overlays/annotations/color-key",
        params={"document_id": "doc-9", "vault_path": "vault/doc-9"},
        json={"colors": colors},
    )
    first = put({"yellow": "first meaning"})
    second = put({"yellow": "revised meaning"})
    assert first.status_code == 200 and second.status_code == 200
    assert second.json()["updated"] is True
    assert second.json()["overlay_id"] == first.json()["overlay_id"]
    # Still exactly one DOCUMENT_KEY overlay for the document
    keys = [ov for ov in client.fake_manager.store.values() if ov.overlay_type == OverlayType.DOCUMENT_KEY]
    assert len(keys) == 1


def test_color_key_put_rejects_empty(client):
    r = client.put(
        "/api/unified-overlays/annotations/color-key",
        params={"document_id": "doc-1", "vault_path": "vault/doc-1"},
        json={"colors": {}},
    )
    assert r.status_code == 400


def test_add_footnote(client):
    r = client.post(
        "/api/unified-overlays/annotations/footnote",
        params={
            "document_id": "doc-1",
            "vault_path": "vault/doc-1",
            "number": 2,
            "content": "Settlement shows a different date than the signed copy",
            "citation": "Settlement ¶3",
        },
        json={"start_offset": 10, "end_offset": 25, "text": "December 23, 2025"},
    )
    assert r.status_code == 200
    assert r.json()["success"] is True
    req = client.fake_manager.created_requests[-1]
    assert req.overlay_type == OverlayType.FOOTNOTE
    assert req.payload["number"] == 2
    assert req.payload["range"]["text"] == "December 23, 2025"
    assert req.payload["citation"] == "Settlement ¶3"


def test_highlight_range_without_offsets_accepted(client):
    """Regression: existing callers send quote/page ranges without offsets."""
    r = client.post(
        "/api/unified-overlays/annotations/highlight",
        params={"document_id": "doc-1", "vault_path": "vault/doc-1", "color": "green"},
        json={"text": "rent due", "page": 1, "x": 10, "y": 20, "width": 40, "height": 8},
    )
    assert r.status_code == 200
    assert r.json()["success"] is True
