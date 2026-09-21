"""Info Donation — service + endpoint tests.

Covers the spec's hard rules: resolution gate first, versioned informed
consent, per-item opt-in validated against the catalog, PII screening on
free text, moderation queue for narrative items, per-item and withdraw-all
revocation, and no cross-user leakage.

Run: python -m pytest tests/test_info_donation.py -q --no-cov
"""

import pytest

from app.modules.info_donation import service
from app.modules.info_donation.catalog import CONSENT_VERSION
from app.modules.info_donation.models import InfoDonationItem, InfoDonationProfile  # noqa: F401 — registers tables

UID = "GUdonor001"
OTHER_UID = "GUdonor002"


async def _resolved_consented(db, user_id: str = UID) -> None:
    await service.mark_resolved(db, user_id)
    await service.record_consent(db, user_id, CONSENT_VERSION)


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------


async def test_status_starts_closed(db_session):
    status = await service.get_status(db_session, UID)
    assert status == {
        "resolved": False,
        "dismissed": False,
        "consented": False,
        "eligible": False,
        "item_count": 0,
        "consent_version": None,
        "current_consent_version": CONSENT_VERSION,
    }


async def test_mark_resolved_opens_gate_and_is_idempotent(db_session):
    assert await service.mark_resolved(db_session, UID) is True
    first = (await service.get_status(db_session, UID))
    assert first["resolved"] is True
    assert first["eligible"] is True
    # Second call is a no-op
    assert await service.mark_resolved(db_session, UID) is False
    profile = await db_session.get(InfoDonationProfile, UID)
    resolved_at = profile.resolved_at
    await service.mark_resolved(db_session, UID)
    assert profile.resolved_at == resolved_at


async def test_dismiss_closes_gate(db_session):
    await service.mark_resolved(db_session, UID)
    await service.dismiss(db_session, UID)
    status = await service.get_status(db_session, UID)
    assert status["resolved"] is True
    assert status["dismissed"] is True
    assert status["eligible"] is False


# ---------------------------------------------------------------------------
# Consent
# ---------------------------------------------------------------------------


async def test_consent_requires_resolution(db_session):
    with pytest.raises(service.DonationError):
        await service.record_consent(db_session, UID, CONSENT_VERSION)


async def test_consent_requires_current_version(db_session):
    await service.mark_resolved(db_session, UID)
    with pytest.raises(service.DonationError):
        await service.record_consent(db_session, UID, "1999-01-01")


# ---------------------------------------------------------------------------
# Donate
# ---------------------------------------------------------------------------


async def test_donate_requires_consent(db_session):
    await service.mark_resolved(db_session, UID)
    with pytest.raises(service.DonationError):
        await service.submit_items(db_session, UID, {"outcome": "resolved"})


async def test_donate_validates_catalog(db_session):
    await _resolved_consented(db_session)
    with pytest.raises(service.DonationError):
        await service.submit_items(db_session, UID, {"landlord_name": "Acme"})
    with pytest.raises(service.DonationError):
        await service.submit_items(db_session, UID, {"outcome": "won_the_lottery"})
    with pytest.raises(service.DonationError):
        await service.submit_items(db_session, UID, {"issue_kinds": ["repairs", "aliens"]})
    with pytest.raises(service.DonationError):
        await service.submit_items(db_session, UID, {})


async def test_donate_categorical_stores_immediately(db_session):
    await _resolved_consented(db_session)
    stored = await service.submit_items(
        db_session,
        UID,
        {"outcome": "resolved", "stayed_in_home": True, "issue_kinds": ["repairs", "deposit"]},
    )
    assert len(stored) == 3
    assert all(i.moderation == "none" for i in stored)


async def test_free_text_goes_to_pending_and_is_pii_screened(db_session):
    await _resolved_consented(db_session)
    stored = await service.submit_items(db_session, UID, {"wish_known": "Take photos on day one."})
    assert stored[0].moderation == "pending"

    for bad in (
        "call me at 612-555-0142",
        "email me at tenant@example.com",
        "my ssn is 123-45-6789",
        "I live at 123 Main Street",
    ):
        with pytest.raises(service.DonationError):
            await service.submit_items(db_session, UID, {"wish_known": bad})


async def test_reanswer_replaces_and_requeues_review(db_session):
    await _resolved_consented(db_session)
    await service.submit_items(db_session, UID, {"wish_known": "first answer"})
    item = (await service.list_mine(db_session, UID))[0]
    await service.moderate_item(db_session, item.id, "approved", "admin1")

    await service.submit_items(db_session, UID, {"wish_known": "better answer"})
    item = (await service.list_mine(db_session, UID))[0]
    assert item.moderation == "pending"
    import json

    assert json.loads(item.value_json) == "better answer"


# ---------------------------------------------------------------------------
# Withdrawal + moderation
# ---------------------------------------------------------------------------


async def test_withdraw_item_is_owner_only(db_session):
    await _resolved_consented(db_session)
    stored = await service.submit_items(db_session, UID, {"outcome": "resolved"})
    item_id = stored[0].id
    assert await service.withdraw_item(db_session, OTHER_UID, item_id) is False
    assert await service.withdraw_item(db_session, UID, item_id) is True
    assert (await service.list_mine(db_session, UID)) == []


async def test_withdraw_all_deletes_and_revokes(db_session):
    await _resolved_consented(db_session)
    await service.submit_items(db_session, UID, {"outcome": "resolved", "stayed_in_home": True})
    removed = await service.withdraw_all(db_session, UID)
    assert removed == 2
    status = await service.get_status(db_session, UID)
    assert status["consented"] is False
    assert status["item_count"] == 0
    with pytest.raises(service.DonationError):
        await service.submit_items(db_session, UID, {"outcome": "resolved"})


async def test_moderation_flow(db_session):
    await _resolved_consented(db_session)
    await service.submit_items(db_session, UID, {"feedback": "The letters page was clear."})
    pending = await service.list_pending_review(db_session)
    assert len(pending) == 1
    item = await service.moderate_item(db_session, pending[0].id, "approved", "admin1")
    assert item.moderation == "approved"
    assert item.moderated_by == "admin1"
    assert (await service.list_pending_review(db_session)) == []
    with pytest.raises(service.DonationError):
        await service.moderate_item(db_session, item.id, "maybe", "admin1")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


async def test_endpoints_require_auth(client):
    resp = await client.get("/api/info-donation/status")
    assert resp.status_code == 401
    resp = await client.post("/api/info-donation/resolved", json={"source": "self_reported"})
    assert resp.status_code == 401


async def test_full_donation_flow_over_http(authenticated_client):
    # Gate is closed until the tenant marks resolved
    resp = await authenticated_client.get("/api/info-donation/status")
    assert resp.status_code == 200
    assert resp.json()["resolved"] is False

    resp = await authenticated_client.post(
        "/api/info-donation/donate", json={"items": {"outcome": "resolved"}}
    )
    assert resp.status_code == 422

    resp = await authenticated_client.post("/api/info-donation/resolved", json={})
    assert resp.status_code == 200

    resp = await authenticated_client.post(
        "/api/info-donation/consent", json={"consent_version": CONSENT_VERSION}
    )
    assert resp.status_code == 200

    resp = await authenticated_client.post(
        "/api/info-donation/donate",
        json={"items": {"outcome": "resolved", "wish_known": "Read the lease twice."}},
    )
    assert resp.status_code == 200
    stored = {i["item_key"]: i for i in resp.json()["stored"]}
    assert stored["outcome"]["moderation"] == "none"
    assert stored["wish_known"]["moderation"] == "pending"

    resp = await authenticated_client.get("/api/info-donation/mine")
    assert len(resp.json()["items"]) == 2

    # Non-admin cannot reach the review queue
    resp = await authenticated_client.get("/api/info-donation/review/pending")
    assert resp.status_code == 403

    resp = await authenticated_client.post("/api/info-donation/withdraw-all")
    assert resp.status_code == 200
    assert resp.json()["removed_count"] == 2

    resp = await authenticated_client.get("/api/info-donation/mine")
    assert resp.json()["items"] == []
