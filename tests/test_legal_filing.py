import pytest

from app.models.legal_filing_models import LegalCase


@pytest.mark.anyio
async def test_get_seed_cases(client):
    response = await client.get("/api/legal-filing/cases")
    assert response.status_code == 200
    cases = response.json()
    assert isinstance(cases, list)
    assert any(c.get("case_id") == "C001" for c in cases)
    assert any(c.get("case_id") == "C002" for c in cases)


@pytest.mark.anyio
async def test_get_case_by_id(client):
    response = await client.get("/api/legal-filing/cases/C001")
    assert response.status_code == 200
    assert response.json()["case_id"] == "C001"


@pytest.mark.anyio
async def test_get_nonexistent_case(client):
    response = await client.get("/api/legal-filing/cases/NOPE")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_create_new_case_roundtrip(client):
    new_case = {
        "case_id": "C003",
        "tenant_name": "New Tenant",
        "landlord_name": "New Landlord",
        "address": "789 Elm St",
        "status": "draft",
    }

    create_resp = await client.post(
        "/api/legal-filing/cases",
        json=new_case,
        cookies={"semptify_uid": "GVtest1234"},  # advocate role
    )
    assert create_resp.status_code == 200
    body = create_resp.json()
    assert body["status"] == "created"
    assert body["case"]["case_id"] == "C003"

    get_resp = await client.get("/api/legal-filing/cases/C003")
    assert get_resp.status_code == 200
    assert get_resp.json()["tenant_name"] == "New Tenant"


@pytest.mark.anyio
async def test_create_case_denied_for_user_role(client):
    # default cookie from setup is GUtest1234 => user role
    new_case = {
        "case_id": "C004",
        "tenant_name": "Denied Tenant",
        "landlord_name": "Denied Landlord",
        "address": "1010 Denied St",
        "status": "draft",
    }

    create_resp = await client.post("/api/legal-filing/cases", json=new_case)
    assert create_resp.status_code == 403


@pytest.mark.anyio
async def test_create_case_ok_for_advocate_role(client):
    new_case = {
        "case_id": "C005",
        "tenant_name": "Advocate Tenant",
        "landlord_name": "Advocate Landlord",
        "address": "1212 Advocate Ave",
        "status": "draft",
    }

    create_resp = await client.post(
        "/api/legal-filing/cases",
        json=new_case,
        cookies={"semptify_uid": "GVtest1234"},
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["case"]["case_id"] == "C005"


@pytest.mark.anyio
async def test_evidence_api_roles_and_data(client):
    # create a case with advocate role
    case_payload = {
        "case_id": "C006",
        "tenant_name": "Evidence Tenant",
        "landlord_name": "Evidence Landlord",
        "address": "1313 Evidence Blvd",
        "status": "draft",
    }

    create_case_resp = await client.post(
        "/api/legal-filing/cases",
        json=case_payload,
        cookies={"semptify_uid": "GVtest1234"},
    )
    assert create_case_resp.status_code == 200

    evidence_payload = {
        "item_id": "E001",
        "case_id": "C006",
        "description": "Photo of damaged ceiling",
        "collected_on": "2026-04-01",
        "tags": ["ceiling", "damage"],
    }

    add_resp = await client.post(
        "/api/legal-filing/cases/C006/evidence",
        json=evidence_payload,
        cookies={"semptify_uid": "GVtest1234"},
    )
    assert add_resp.status_code == 200
    assert add_resp.json()["status"] == "evidence added"

    list_resp = await client.get(
        "/api/legal-filing/cases/C006/evidence",
        cookies={"semptify_uid": "GUtest1234"},
    )
    assert list_resp.status_code == 200
    evidence_list = list_resp.json()
    assert isinstance(evidence_list, list)
    assert evidence_list[0]["item_id"] == "E001"
