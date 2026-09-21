"""Integration smoke test for Document Center gap fills.

Verifies:
- Review state persistence (GET/POST /api/dc/document/{id}/review-state)
- Manual verification status drives /api/dc/list
- Real share creation and listing
"""

import hashlib

import pytest

from app.core.cookie_auth import sign_user_id
from app.core.utc import utc_now


@pytest.mark.anyio
async def test_dc_review_state_and_share(client, db_session):
    """Persist field confirm/correct state, manual status, and real shares."""
    from app.models.models import User, VaultIndexDB

    user_id = "GUtest1234"
    user = User(
        id=user_id,
        primary_provider="local",
        storage_user_id=user_id,
        default_role="user",
    )
    db_session.add(user)

    vault_id = "doc_test1234"
    doc = VaultIndexDB(
        vault_id=vault_id,
        user_id=user_id,
        filename="lease.pdf",
        safe_filename="lease.pdf",
        sha256_hash=hashlib.sha256(b"mock").hexdigest(),
        file_size=100,
        mime_type="application/pdf",
        storage_path="data/vault/test/lease.pdf",
        storage_provider="local",
        uploaded_at=utc_now(),
    )
    db_session.add(doc)
    await db_session.commit()

    signed = sign_user_id(user_id)
    client.cookies.update({"semptify_uid": signed})

    # List shows the stored file in the pending lane — its required fields
    # have not been answered, so it is not a filed document yet (F1.4).
    r = await client.get("/api/dc/list")
    assert r.status_code == 200
    data = r.json()
    assert any(
        d["id"] == vault_id and d["verification_state"] == "unverified"
        for d in data["pending_documents"]
    )
    assert not any(d["id"] == vault_id for d in data["documents"])
    assert "processed_document_count" in data

    # Review state starts empty
    r = await client.get(f"/api/dc/document/{vault_id}/review-state")
    assert r.status_code == 200
    assert r.json()["effective_status"] == "unverified"

    # Save review state
    r = await client.post(
        f"/api/dc/document/{vault_id}/review-state",
        json={
            "manual_status": "verified",
            "field_confirm_state": {"landlord_name": "confirmed"},
        },
    )
    assert r.status_code == 200
    assert r.json()["effective_status"] == "verified"

    # List reflects verified status — the explicit manual status files the
    # document (the tenant deliberately marked it, so it leaves pending).
    r = await client.get("/api/dc/list")
    assert r.status_code == 200
    assert any(
        d["id"] == vault_id and d["verification_state"] == "verified"
        for d in r.json()["documents"]
    )

    # Re-fetch review state
    r = await client.get(f"/api/dc/document/{vault_id}/review-state")
    assert r.status_code == 200
    assert r.json()["manual_status"] == "verified"
    assert r.json()["field_confirm_state"]["landlord_name"] == "confirmed"


@pytest.mark.anyio
@pytest.mark.xfail(
    reason=(
        "Share endpoints require a provisioned cloud vault — since #280 shares "
        "persist as DOCUMENT_SHARE overlays in the owner's vault, and this "
        "fixture's user has no session/token (build_context_for_user_id -> "
        "503). Share behavior is covered by tests/test_document_share_vault.py."
    ),
    strict=False,
)
async def test_dc_share_requires_cloud_vault(client, db_session):
    """Create and list a real share — needs a tokened cloud-vault user."""
    from app.models.models import User, VaultIndexDB

    user_id = "GUtest1234"
    user = User(
        id=user_id,
        primary_provider="local",
        storage_user_id=user_id,
        default_role="user",
    )
    db_session.add(user)

    vault_id = "doc_test1234"
    doc = VaultIndexDB(
        vault_id=vault_id,
        user_id=user_id,
        filename="lease.pdf",
        safe_filename="lease.pdf",
        sha256_hash=hashlib.sha256(b"mock").hexdigest(),
        file_size=100,
        mime_type="application/pdf",
        storage_path="data/vault/test/lease.pdf",
        storage_provider="local",
        uploaded_at=utc_now(),
    )
    db_session.add(doc)
    await db_session.commit()

    signed = sign_user_id(user_id)
    client.cookies.update({"semptify_uid": signed})

    # Create a real share
    r = await client.post(
        f"/api/dc/document/{vault_id}/share",
        json={"recipient": "advocate@example.com", "scope": "view"},
    )
    assert r.status_code == 200
    token = r.json()["share_token"]
    assert token

    # List shares
    r = await client.get(f"/api/dc/document/{vault_id}/shares")
    assert r.status_code == 200
    assert any(s["share_token"] == token for s in r.json()["shares"])
