import pytest

from app.routers import document_overlays as overlay_router
from app.services.document_overlay_service import DocumentOverlayService


@pytest.fixture
def isolated_overlay_service(tmp_path, monkeypatch):
    service = DocumentOverlayService(store_path=tmp_path / "overlay_records.json")
    monkeypatch.setattr(overlay_router, "document_overlay_service", service)
    return service


@pytest.mark.anyio
async def test_document_overlay_health(client):
    response = await client.get("/api/document-overlays/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "document_overlays_v2"


@pytest.mark.anyio
async def test_create_list_get_overlay_record(client, isolated_overlay_service):
    create_response = await client.post(
        "/api/document-overlays/records",
        json={
            "document_id": "doc-123",
            "vault_id": "vault-123",
            "overlay_type": "annotation",
            "payload": {"note": "lease discrepancy"},
            "metadata": {"source": "manual"},
        },
        cookies={"semptify_uid": "GVtest1234"},
    )
    assert create_response.status_code == 200
    created = create_response.json()
    overlay_id = created["overlay_id"]

    list_response = await client.get(
        "/api/document-overlays/records",
        params={"document_id": "doc-123"},
        cookies={"semptify_uid": "GUtest1234"},
    )
    assert list_response.status_code == 200
    listed = list_response.json()
    assert len(listed) == 1
    assert listed[0]["overlay_id"] == overlay_id

    get_response = await client.get(
        f"/api/document-overlays/records/{overlay_id}",
        cookies={"semptify_uid": "GUtest1234"},
    )
    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["document_id"] == "doc-123"
    assert fetched["overlay_type"] == "annotation"


@pytest.mark.anyio
async def test_apply_overlay_record_dry_run_and_real(client, isolated_overlay_service):
    create_response = await client.post(
        "/api/document-overlays/records",
        json={
            "document_id": "doc-456",
            "overlay_type": "processing",
            "payload": {"entities": ["tenant", "landlord"]},
        },
        cookies={"semptify_uid": "GVtest1234"},
    )
    overlay_id = create_response.json()["overlay_id"]

    dry_run_response = await client.post(
        f"/api/document-overlays/records/{overlay_id}/apply",
        json={"dry_run": True},
        cookies={"semptify_uid": "GVtest1234"},
    )
    assert dry_run_response.status_code == 200
    dry_payload = dry_run_response.json()
    assert dry_payload["dry_run"] is True
    assert dry_payload["status"] == "draft"

    apply_response = await client.post(
        f"/api/document-overlays/records/{overlay_id}/apply",
        json={"dry_run": False},
        cookies={"semptify_uid": "GVtest1234"},
    )
    assert apply_response.status_code == 200
    apply_payload = apply_response.json()
    assert apply_payload["dry_run"] is False
    assert apply_payload["status"] == "applied"


@pytest.mark.anyio
async def test_overlay_record_write_denied_for_user_role(client, isolated_overlay_service):
    response = await client.post(
        "/api/document-overlays/records",
        json={
            "document_id": "doc-789",
            "overlay_type": "annotation",
            "payload": {"text": "forbidden"},
        },
        cookies={"semptify_uid": "GUtest1234"},
    )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_overlay_create_and_apply_emit_event_and_audit(client, isolated_overlay_service, monkeypatch):
    published = []
    audited = []

    def fake_publish_sync(event_type, data, source="system", user_id=None):
        published.append(
            {
                "event_type": event_type.value,
                "data": data,
                "source": source,
                "user_id": user_id,
            }
        )

    async def fake_audit_log(**kwargs):
        audited.append(kwargs)

    monkeypatch.setattr(overlay_router.event_bus, "publish_sync", fake_publish_sync)
    monkeypatch.setattr(overlay_router, "audit_log", fake_audit_log)

    create_response = await client.post(
        "/api/document-overlays/records",
        json={
            "document_id": "doc-audit",
            "overlay_type": "annotation",
            "payload": {"text": "hello"},
        },
        cookies={"semptify_uid": "GVtest1234"},
    )
    overlay_id = create_response.json()["overlay_id"]

    apply_response = await client.post(
        f"/api/document-overlays/records/{overlay_id}/apply",
        json={"dry_run": False},
        cookies={"semptify_uid": "GVtest1234"},
    )

    assert apply_response.status_code == 200
    assert any(item["data"].get("action") == "overlay_record_created" for item in published)
    assert any(item["data"].get("action") == "overlay_record_applied" for item in published)
    assert any(item.get("resource_id") == overlay_id for item in audited)
