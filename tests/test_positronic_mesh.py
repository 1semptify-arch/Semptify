"""
Tests for the Positronic Mesh router.

Covers: status, available workflows, workflow start/get, user workflow list,
quick-start convenience endpoints, and module invocation error paths.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

USER_COOKIE = {"semptify_uid": "GUa8Km3xPq"}


# =============================================================================
# Mesh Status
# =============================================================================

class TestMeshStatus:
    def test_get_status_ok(self):
        resp = client.get("/mesh/status")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_get_available_workflows(self):
        resp = client.get("/mesh/workflows/available")
        assert resp.status_code == 200
        data = resp.json()
        assert "workflows" in data
        assert "types" in data
        assert isinstance(data["types"], list)
        assert len(data["types"]) > 0

    def test_get_connected_modules(self):
        resp = client.get("/mesh/modules")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_modules" in data
        assert "modules" in data


# =============================================================================
# Workflow Start / Get
# =============================================================================

class TestWorkflowLifecycle:
    def test_start_invalid_workflow_type(self):
        resp = client.post("/mesh/workflow/start", json={
            "workflow_type": "not_a_real_type",
        }, cookies=USER_COOKIE)
        assert resp.status_code == 400
        assert "Invalid workflow type" in resp.json().get("detail", "")

    def test_start_eviction_workflow(self):
        resp = client.post("/mesh/workflow/start", json={
            "workflow_type": "eviction_defense",
            "initial_context": {"test": True},
            "trigger": "test_suite",
        }, cookies=USER_COOKIE)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "workflow" in data
        workflow_id = data["workflow"]["id"]
        assert workflow_id

        # Retrieve the workflow
        get_resp = client.get(f"/mesh/workflow/{workflow_id}", cookies=USER_COOKIE)
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == workflow_id

    def test_get_nonexistent_workflow(self):
        resp = client.get("/mesh/workflow/does-not-exist-xyz", cookies=USER_COOKIE)
        assert resp.status_code == 404

    def test_get_user_workflows_empty_then_populated(self):
        # Start a workflow so there's at least one
        client.post("/mesh/workflow/start", json={
            "workflow_type": "lease_analysis",
            "trigger": "test_suite",
        }, cookies=USER_COOKIE)

        resp = client.get("/mesh/workflows", cookies=USER_COOKIE)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "workflows" in data
        assert isinstance(data["workflows"], list)


# =============================================================================
# Quick-Start Endpoints
# =============================================================================

class TestQuickStartEndpoints:
    def test_quick_eviction(self):
        resp = client.post("/mesh/quick/eviction", json={}, cookies=USER_COOKIE)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "workflow_id" in data

    def test_quick_lease_analysis(self):
        resp = client.post("/mesh/quick/lease-analysis", json={}, cookies=USER_COOKIE)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_quick_court_prep(self):
        resp = client.post("/mesh/quick/court-prep", json={}, cookies=USER_COOKIE)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_quick_sync(self):
        resp = client.post("/mesh/quick/sync", cookies=USER_COOKIE)
        assert resp.status_code == 200
        assert resp.json()["success"] is True


# =============================================================================
# Module Actions
# =============================================================================

class TestModuleActions:
    def test_get_actions_nonexistent_module(self):
        resp = client.get("/mesh/module/totally_fake_module_xyz/actions")
        assert resp.status_code == 404

    def test_invoke_nonexistent_module(self):
        resp = client.post("/mesh/invoke", json={
            "module": "nonexistent",
            "action": "do_nothing",
            "params": {},
        }, cookies=USER_COOKIE)
        assert resp.status_code == 404
