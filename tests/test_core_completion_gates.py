from uuid import uuid4

import pytest

from app.routers import document_overlays as overlay_router
from app.services.document_overlay_service import DocumentOverlayService
from app.services.vault_upload_service import VaultDocumentIndex, VaultUploadService


@pytest.fixture(name="isolated_overlay_service")
def fixture_isolated_overlay_service(tmp_path, monkeypatch):
    service = DocumentOverlayService(store_path=tmp_path / "overlay_records.json")
    monkeypatch.setattr("app.services.document_overlay_service.document_overlay_service", service)
    monkeypatch.setattr(overlay_router, "document_overlay_service", service)
    return service


@pytest.fixture(name="isolated_vault_service")
def fixture_isolated_vault_service(tmp_path, monkeypatch):
    service = VaultUploadService()
    service.index = VaultDocumentIndex(data_dir=str(tmp_path / "vault_index"))
    local_dir = tmp_path / "vault_storage"
    local_dir.mkdir(parents=True, exist_ok=True)
    setattr(service, "_local_dir", local_dir)
    monkeypatch.setattr("app.services.vault_upload_service._vault_service", service)
    return service


@pytest.mark.anyio
@pytest.mark.usefixtures("isolated_overlay_service", "isolated_vault_service")
async def test_gate_end_to_end_filing_path(client):
    user_id = "GUe2e12345"
    case_id = f"CGATE-{uuid4().hex[:8]}"

    upload_response = await client.post(
        "/api/intake/upload",
        data={
            "user_id": user_id,
            "username": "gate_user",
            "storage_provider": "local",
        },
        files={"file": ("notice.pdf", b"notice-body", "application/pdf")},
    )

    assert upload_response.status_code == 200
    upload_payload = upload_response.json()
    assert upload_payload["vault_id"]
    assert upload_payload["overlay_record_ids"]

    overlay_ids = upload_payload["overlay_record_ids"]
    vault_id = upload_payload["vault_id"]

    route_response = await client.post(
        "/api/workflow/route",
        json={
            "role": "user",
            "storage_state": "already_connected",
            "documents_present": False,
            "overlay_record_ids": overlay_ids,
        },
    )

    assert route_response.status_code == 200
    route_payload = route_response.json()
    assert route_payload["next_process"] == "B2"
    assert route_payload["next_route"] == "/tenant"

    create_case_response = await client.post(
        "/api/legal-filing/cases",
        json={
            "case_id": case_id,
            "tenant_name": "Core Gate Tenant",
            "landlord_name": "Core Gate Landlord",
            "address": "100 Core Gate Ave",
        },
        cookies={"semptify_uid": "GVgate12345"},
    )

    assert create_case_response.status_code == 200

    evidence_response = await client.post(
        f"/api/legal-filing/cases/{case_id}/evidence",
        json={
            "item_id": "E-GATE-1",
            "case_id": case_id,
            "description": "Evidence derived from intake overlays",
            "overlay_record_ids": overlay_ids,
        },
        cookies={"semptify_uid": "GVgate12345"},
    )

    assert evidence_response.status_code == 200
    evidence_payload = evidence_response.json()["evidence"]
    assert evidence_payload["vault_id"] == vault_id
    assert evidence_payload["overlay_record_ids"] == overlay_ids
    assert "sha256_hash" in evidence_payload["extracted_data"]



@pytest.mark.anyio
async def test_gate_tenant_isolation_vault_index(isolated_vault_service):
    user_a = "GUtenanta1"
    user_b = "GUtenantb2"

    await isolated_vault_service.upload(
        user_id=user_a,
        filename="a.pdf",
        content=b"user-a-content",
        mime_type="application/pdf",
        source_module="gate-test",
        storage_provider="local",
    )
    await isolated_vault_service.upload(
        user_id=user_b,
        filename="b.pdf",
        content=b"user-b-content",
        mime_type="application/pdf",
        source_module="gate-test",
        storage_provider="local",
    )

    docs_a = isolated_vault_service.get_user_documents(user_a)
    docs_b = isolated_vault_service.get_user_documents(user_b)

    assert len(docs_a) == 1
    assert len(docs_b) == 1
    assert docs_a[0].user_id == user_a
    assert docs_b[0].user_id == user_b
    assert docs_a[0].vault_id != docs_b[0].vault_id


@pytest.mark.anyio
async def test_gate_tenant_isolation_overlay_write_permissions(client):
    denied_response = await client.post(
        "/api/document-overlays/records",
        json={
            "document_id": "doc-tenant-check",
            "vault_id": "vault-tenant-check",
            "overlay_type": "annotation",
            "payload": {"note": "should fail for user role"},
        },
        cookies={"semptify_uid": "GUscope1234"},
    )
    assert denied_response.status_code == 403

    allowed_response = await client.post(
        "/api/document-overlays/records",
        json={
            "document_id": "doc-tenant-check",
            "vault_id": "vault-tenant-check",
            "overlay_type": "annotation",
            "payload": {"note": "allowed for advocate role"},
        },
        cookies={"semptify_uid": "GVscope1234"},
    )
    assert allowed_response.status_code == 200


@pytest.mark.anyio
async def test_gate_workflow_integrity_blocks_missing_requirements(client):
    response = await client.post(
        "/api/workflow/advance",
        json={
            "current_page": "welcome",
            "role": "user",
            "storage_state": "already_connected",
            "completed_actions": [],
            "documents_present": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert set(payload["missing_requirements"]) == {
        "role_selected",
        "storage_status_set",
        "process_start_clicked",
    }


@pytest.mark.anyio
async def test_gate_workflow_integrity_rejects_invalid_inputs(client):
    bad_role_response = await client.post(
        "/api/workflow/route",
        json={
            "role": "not-a-real-role",
            "storage_state": "already_connected",
        },
    )
    assert bad_role_response.status_code == 422

    bad_page_response = await client.post(
        "/api/workflow/advance",
        json={
            "current_page": "tenant_help",
            "role": "user",
            "storage_state": "already_connected",
            "completed_actions": [
                "role_selected",
                "storage_status_set",
                "process_start_clicked",
            ],
        },
    )
    assert bad_page_response.status_code == 422


@pytest.mark.anyio
async def test_gate_workflow_integrity_advances_with_overlay_signal(client):
    response = await client.post(
        "/api/workflow/advance",
        json={
            "current_page": "welcome",
            "role": "user",
            "storage_state": "already_connected",
            "completed_actions": [
                "role_selected",
                "storage_status_set",
                "process_start_clicked",
            ],
            "documents_present": False,
            "overlay_record_ids": ["ovl_signal_1"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "advance"
    assert payload["next_process"] == "B2"
    assert payload["next_route"] == "/tenant"
