"""
Tests for the Plan Maker module.

Covers:
  - Service layer: create_plan, add_entity, add_evidence, add_next_step,
    mark_step_complete, to_markdown, to_json, plan_from_dict round-trip
  - Router: create, view, export (markdown + json), add entity/evidence/step,
    complete step, default-steps template, auth enforcement, ownership guard
"""

import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.plan_maker_service import (
    create_plan,
    add_entity,
    add_evidence,
    add_next_step,
    mark_step_complete,
    plan_from_dict,
    EntityRecord,
    EvidenceItem,
    NextStep,
)

client = TestClient(app)
USER_COOKIE = {"semptify_uid": "GUa8Km3xPq"}


# =============================================================================
# Service Layer Tests
# =============================================================================

class TestPlanMakerService:
    def test_create_plan_defaults(self):
        plan = create_plan(user_id="user-1", title="Test Plan")
        assert plan.plan_id.startswith("PLAN-")
        assert plan.user_id == "user-1"
        assert plan.title == "Test Plan"
        assert len(plan.next_steps) > 0  # default steps populated
        assert len(plan.modules_needed) > 0

    def test_create_plan_no_default_steps(self):
        plan = create_plan(user_id="u1", title="Empty", include_default_steps=False)
        assert plan.next_steps == []

    def test_create_plan_with_issues(self):
        plan = create_plan(
            user_id="u1",
            title="Eviction Defense",
            landlord_name="Velair Property",
            issues=["Retaliation", "Delayed repairs"],
            desired_outcomes="Maintain housing",
        )
        assert "Retaliation" in plan.issues
        assert plan.landlord_name == "Velair Property"

    def test_add_entity(self):
        plan = create_plan(user_id="u1", title="T")
        updated = add_entity(plan, EntityRecord(name="Velair LLC", role="landlord", address="123 Main"))
        assert len(updated.entities) == 1
        assert updated.entities[0].name == "Velair LLC"

    def test_add_evidence(self):
        plan = create_plan(user_id="u1", title="T")
        updated = add_evidence(plan, EvidenceItem(description="Eviction notice", vault_id="v-001"))
        assert len(updated.evidence_items) == 1
        assert updated.evidence_items[0].vault_id == "v-001"

    def test_add_next_step(self):
        plan = create_plan(user_id="u1", title="T", include_default_steps=False)
        updated = add_next_step(plan, NextStep(action="Send certified letter", due_date="2026-05-01"))
        assert len(updated.next_steps) == 1
        assert updated.next_steps[0].action == "Send certified letter"
        assert not updated.next_steps[0].completed

    def test_mark_step_complete(self):
        plan = create_plan(user_id="u1", title="T")
        updated = mark_step_complete(plan, 0)
        assert updated.next_steps[0].completed is True

    def test_mark_step_out_of_range(self):
        plan = create_plan(user_id="u1", title="T", include_default_steps=False)
        # Should not raise, just be a no-op
        updated = mark_step_complete(plan, 99)
        assert updated.next_steps == []

    def test_to_markdown_contains_key_sections(self):
        plan = create_plan(
            user_id="u1",
            title="My Plan",
            landlord_name="Bad Landlord",
            issues=["No heat"],
        )
        md = plan.to_markdown()
        assert "# Accountability Plan" in md
        assert "Bad Landlord" in md
        assert "No heat" in md
        assert "## 6. Next Steps" in md

    def test_to_json_round_trip(self):
        plan = create_plan(user_id="u1", title="Round Trip")
        add_entity(plan, EntityRecord(name="Test Corp"))
        raw = plan.to_json()
        data = json.loads(raw)
        restored = plan_from_dict(data)
        assert restored.plan_id == plan.plan_id
        assert restored.entities[0].name == "Test Corp"

    def test_plan_from_dict_round_trip(self):
        plan = create_plan(user_id="u2", title="RT", issues=["Issue 1"])
        d = plan.to_dict()
        restored = plan_from_dict(d)
        assert restored.user_id == "u2"
        assert "Issue 1" in restored.issues


# =============================================================================
# Router Tests
# =============================================================================

class TestPlanMakerRouter:

    # --- Auth enforcement ---

    def test_create_plan_requires_auth(self):
        resp = client.post("/api/plan-maker/plans", json={"title": "No auth"})
        assert resp.status_code in (401, 403)

    def test_default_steps_public(self):
        resp = client.get("/api/plan-maker/templates/default-steps")
        assert resp.status_code == 200
        data = resp.json()
        assert "default_steps" in data
        assert "default_modules" in data
        assert isinstance(data["default_steps"], list)
        assert len(data["default_steps"]) > 0

    # --- Create plan ---

    def test_create_plan(self):
        resp = client.post("/api/plan-maker/plans", json={
            "title": "Eviction Defense",
            "landlord_name": "Velair Property Management",
            "property_name": "Lexington Flats",
            "issues": ["Retaliation", "No heat"],
            "desired_outcomes": "Keep housing",
        }, cookies=USER_COOKIE)
        assert resp.status_code == 200
        data = resp.json()
        assert "plan_id" in data
        assert data["plan"]["landlord_name"] == "Velair Property Management"
        assert "Retaliation" in data["plan"]["issues"]

    def _fresh_plan(self) -> dict:
        resp = client.post("/api/plan-maker/plans", json={
            "title": "Test Plan",
            "landlord_name": "Test Landlord",
        }, cookies=USER_COOKIE)
        return resp.json()["plan"]

    # --- View plan ---

    def test_view_plan(self):
        plan = self._fresh_plan()
        resp = client.post(
            f"/api/plan-maker/plans/{plan['plan_id']}/view",
            json={"plan": plan},
            cookies=USER_COOKIE,
        )
        assert resp.status_code == 200
        assert resp.json()["plan_id"] == plan["plan_id"]

    def test_view_plan_id_mismatch(self):
        plan = self._fresh_plan()
        resp = client.post(
            "/api/plan-maker/plans/WRONG-ID/view",
            json={"plan": plan},
            cookies=USER_COOKIE,
        )
        assert resp.status_code == 400

    # --- Export ---

    def test_export_markdown(self):
        plan = self._fresh_plan()
        resp = client.post(
            f"/api/plan-maker/plans/{plan['plan_id']}/export?format=markdown",
            json={"plan": plan},
            cookies=USER_COOKIE,
        )
        assert resp.status_code == 200
        assert "text/markdown" in resp.headers["content-type"]
        assert "# Accountability Plan" in resp.text

    def test_export_json(self):
        plan = self._fresh_plan()
        resp = client.post(
            f"/api/plan-maker/plans/{plan['plan_id']}/export?format=json",
            json={"plan": plan},
            cookies=USER_COOKIE,
        )
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]
        data = json.loads(resp.text)
        assert data["plan_id"] == plan["plan_id"]

    # --- Add entity ---

    def test_add_entity(self):
        plan = self._fresh_plan()
        resp = client.post(
            f"/api/plan-maker/plans/{plan['plan_id']}/entity",
            json={
                "plan": plan,
                "name": "Velair LLC",
                "role": "landlord",
                "address": "7645 Lyndale Ave S",
                "registered_agent": "CT Corp",
                "notes": "",
            },
            cookies=USER_COOKIE,
        )
        assert resp.status_code == 200, resp.text
        updated = resp.json()["plan"]
        assert any(e["name"] == "Velair LLC" for e in updated["entities"])

    # --- Add evidence ---

    def test_add_evidence(self):
        plan = self._fresh_plan()
        resp = client.post(
            f"/api/plan-maker/plans/{plan['plan_id']}/evidence",
            json={
                "plan": plan,
                "description": "Eviction notice dated Jan 2026",
                "vault_id": "vault-abc-001",
                "status": "attached",
                "date_obtained": None,
            },
            cookies=USER_COOKIE,
        )
        assert resp.status_code == 200, resp.text
        updated = resp.json()["plan"]
        assert any(ev["vault_id"] == "vault-abc-001" for ev in updated["evidence_items"])

    # --- Add step ---

    def test_add_step(self):
        plan = self._fresh_plan()
        resp = client.post(
            f"/api/plan-maker/plans/{plan['plan_id']}/steps",
            json={
                "plan": plan,
                "action": "File with HUD by June 1",
                "due_date": "2026-06-01",
                "notes": "",
            },
            cookies=USER_COOKIE,
        )
        assert resp.status_code == 200, resp.text
        updated = resp.json()["plan"]
        assert any(s["action"] == "File with HUD by June 1" for s in updated["next_steps"])

    # --- Complete step ---

    def test_complete_step(self):
        plan = self._fresh_plan()
        # Step 0 must exist (default steps are included)
        resp = client.patch(
            f"/api/plan-maker/plans/{plan['plan_id']}/steps/0/complete",
            json={"plan": plan},
            cookies=USER_COOKIE,
        )
        assert resp.status_code == 200
        updated = resp.json()["plan"]
        assert updated["next_steps"][0]["completed"] is True

    def test_complete_step_out_of_range(self):
        plan = self._fresh_plan()
        resp = client.patch(
            f"/api/plan-maker/plans/{plan['plan_id']}/steps/999/complete",
            json={"plan": plan},
            cookies=USER_COOKIE,
        )
        assert resp.status_code == 400
