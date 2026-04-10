import pytest

from app.models.document_overlay_models import DocumentOverlayCreate
from app.services.document_overlay_service import document_overlay_service


@pytest.mark.anyio
async def test_legal_filing_evidence_resolves_overlay_context(client):
    case_id = "COVERLAY1"

    create_case_response = await client.post(
        "/api/legal-filing/cases",
        json={
            "case_id": case_id,
            "tenant_name": "Test Tenant",
            "landlord_name": "Test Landlord",
            "address": "123 Test Ave",
        },
        cookies={"semptify_uid": "GVtest1234"},
    )
    assert create_case_response.status_code == 200

    overlay = document_overlay_service.create_overlay(
        DocumentOverlayCreate(
            document_id="legal-evidence-doc",
            vault_id="vault-legal-1",
            overlay_type="document_extraction",
            payload={"extracted_data": {"summary": "rent ledger mismatch"}},
        )
    )

    response = await client.post(
        f"/api/legal-filing/cases/{case_id}/evidence",
        json={
            "item_id": "E1",
            "case_id": case_id,
            "description": "Overlay evidence",
            "overlay_record_ids": [overlay.overlay_id],
        },
        cookies={"semptify_uid": "GVtest1234"},
    )

    assert response.status_code == 200
    payload = response.json()
    evidence = payload["evidence"]
    assert evidence["vault_id"] == "vault-legal-1"
    assert evidence["overlay_record_ids"] == [overlay.overlay_id]
    assert evidence["extracted_data"]["summary"] == "rent ledger mismatch"
