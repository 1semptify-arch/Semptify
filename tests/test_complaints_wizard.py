"""Tests for the guided complaint wizard flow (start -> answer -> finish).

Wizard sessions are ephemeral and anonymous-safe: finishing without a tenant
cookie returns generated text + filing instructions and stores nothing.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def _walk_to_review(client: AsyncClient) -> str:
    """Run a full wizard walk; returns the session id sitting on 'review'."""
    response = await client.post("/api/complaints/wizard/start", json={"complaint_type": "habitability"})
    assert response.status_code == 200
    state = response.json()
    assert state["step_key"] == "situation"
    session_id = state["session_id"]

    response = await client.post(
        f"/api/complaints/wizard/{session_id}/answer",
        json={"text": "no heat for two weeks, landlord ignored requests"},
    )
    assert response.status_code == 200
    state = response.json()
    assert state["step_key"] == "agency"
    assert state["options"]

    agency_id = state["options"][0]["id"]
    response = await client.post(
        f"/api/complaints/wizard/{session_id}/answer", json={"agency_id": agency_id}
    )
    assert response.status_code == 200
    assert response.json()["step_key"] == "details"

    response = await client.post(
        f"/api/complaints/wizard/{session_id}/answer",
        json={
            "subject": "No heat since October",
            "description": "Furnace broken two weeks; three written requests ignored.",
            "respondent_name": "Test Property LLC",
            "incident_dates": ["2026-10-20"],
            "relief_sought": "Repair the furnace and inspect the unit.",
        },
    )
    assert response.status_code == 200
    return session_id


class TestWizardFlow:
    """Happy-path step progression."""

    @pytest.mark.asyncio
    async def test_start_returns_next_step(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/complaints/wizard/start", json={"complaint_type": "security_deposit"}
            )
            assert response.status_code == 200
            state = response.json()
            assert state["step_key"] == "situation"
            assert state["collected"]["complaint_type"] == "security_deposit"
            assert state["done"] is False

    @pytest.mark.asyncio
    async def test_full_walk_reaches_review(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            session_id = await _walk_to_review(client)
            response = await client.get(f"/api/complaints/wizard/{session_id}")
            assert response.status_code == 200
            state = response.json()
            assert state["step_key"] == "review"
            assert state["summary"]["subject"] == "No heat since October"
            assert state["missing"] == []

    @pytest.mark.asyncio
    async def test_finish_anonymous_returns_prepared(self):
        """Anonymous finish: generated text + instructions, nothing stored."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            session_id = await _walk_to_review(client)
            response = await client.post(f"/api/complaints/wizard/{session_id}/finish")
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "prepared"
            assert "FORMAL COMPLAINT" in result["complaint_text"]
            assert "Test Property LLC" in result["complaint_text"]
            assert result["next_steps"]
            assert result["note"]
            # honest: never claims the complaint was filed
            assert "filed" not in result["status"]

    @pytest.mark.asyncio
    async def test_agency_step_offers_recommendations(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/complaints/wizard/start", json={"complaint_type": "discrimination"}
            )
            session_id = response.json()["session_id"]
            response = await client.post(
                f"/api/complaints/wizard/{session_id}/answer",
                json={"keywords": ["discrimination", "disability"]},
            )
            options = response.json()["options"]
            option_ids = [o["id"] for o in options]
            # discrimination keywords should surface a HUD agency first
            assert option_ids[0].startswith("hud")


class TestWizardValidation:
    """Bad input and unknown sessions get clean errors, not 500s."""

    @pytest.mark.asyncio
    async def test_unknown_session_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/complaints/wizard/wiz_nope")
            assert response.status_code == 404
            response = await client.post(
                "/api/complaints/wizard/wiz_nope/answer", json={"complaint_type": "general"}
            )
            assert response.status_code == 404
            response = await client.post("/api/complaints/wizard/wiz_nope/finish")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_bad_agency_id_422(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/complaints/wizard/start", json={"complaint_type": "general"}
            )
            session_id = response.json()["session_id"]
            await client.post(
                f"/api/complaints/wizard/{session_id}/answer", json={"keywords": ["deposit"]}
            )
            response = await client.post(
                f"/api/complaints/wizard/{session_id}/answer", json={"agency_id": "not_real"}
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_situation_step_requires_input(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/complaints/wizard/start", json={"complaint_type": "general"}
            )
            session_id = response.json()["session_id"]
            response = await client.post(f"/api/complaints/wizard/{session_id}/answer", json={})
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_finished_session_cannot_be_answered(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            session_id = await _walk_to_review(client)
            await client.post(f"/api/complaints/wizard/{session_id}/finish")
            response = await client.post(
                f"/api/complaints/wizard/{session_id}/answer", json={"subject": "x"}
            )
            assert response.status_code == 422


class TestSubmitHonesty:
    """/submit prepares a complaint for the tenant to file — it must never
    claim the complaint was submitted to an agency."""

    @pytest.mark.asyncio
    async def test_submit_anonymous_is_honest(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/complaints/submit",
                json={
                    "agency_id": "mn_ag_consumer",
                    "subject": "Test Complaint",
                    "detailed_description": "Details",
                    "target_name": "Test Landlord LLC",
                },
            )
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "prepared"
            assert result["agency"] == "Minnesota Attorney General - Consumer Protection"
            assert result["next_steps"]
            # the response must not claim anything was filed
            body = response.text.lower()
            assert "submitted to" not in body
            assert "complaint submitted" not in body
