"""
Tests for the Positronic Brain router (/brain/*).

Covers: status, modules list, state CRUD, event history, emit event (valid + invalid),
workflow trigger + get, think, sync, and the 404 workflow path.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# =============================================================================
# Status & Modules
# =============================================================================

class TestBrainStatus:
    def test_get_status(self):
        resp = client.get("/brain/status")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_list_modules(self):
        resp = client.get("/brain/modules")
        assert resp.status_code == 200
        data = resp.json()
        assert "modules" in data
        assert "count" in data
        assert isinstance(data["modules"], list)


# =============================================================================
# Shared State
# =============================================================================

class TestBrainState:
    def test_get_full_state(self):
        resp = client.get("/brain/state")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    def test_get_state_specific_key_missing(self):
        resp = client.get("/brain/state", params={"key": "nonexistent_key_xyz"})
        assert resp.status_code == 200
        data = resp.json()
        assert "nonexistent_key_xyz" in data
        assert data["nonexistent_key_xyz"] is None

    def test_update_and_read_state(self):
        resp = client.put("/brain/state", json={"key": "test_flag", "value": True})
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert resp.json()["key"] == "test_flag"

        read = client.get("/brain/state", params={"key": "test_flag"})
        assert read.status_code == 200
        assert read.json()["test_flag"] is True


# =============================================================================
# Events
# =============================================================================

class TestBrainEvents:
    def test_get_recent_events_default(self):
        resp = client.get("/brain/events")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert "total" in data
        assert isinstance(data["events"], list)

    def test_get_recent_events_limit(self):
        resp = client.get("/brain/events", params={"limit": 5})
        assert resp.status_code == 200
        events = resp.json()["events"]
        assert len(events) <= 5

    def test_emit_event_invalid_type(self):
        resp = client.post("/brain/events", json={
            "event_type": "totally_fake_event_xyz",
            "source_module": "documents",
            "data": {},
        })
        assert resp.status_code == 400
        assert "Invalid" in resp.json()["detail"]

    def test_emit_event_invalid_module(self):
        resp = client.post("/brain/events", json={
            "event_type": "document_uploaded",
            "source_module": "totally_fake_module",
            "data": {},
        })
        assert resp.status_code == 400
        assert "Invalid" in resp.json()["detail"]

    def test_emit_valid_event(self):
        resp = client.post("/brain/events", json={
            "event_type": "document_uploaded",
            "source_module": "documents",
            "data": {"doc_id": "test-001"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "event" in data


# =============================================================================
# Workflows
# =============================================================================

class TestBrainWorkflows:
    def test_list_workflows(self):
        resp = client.get("/brain/workflows")
        assert resp.status_code == 200
        data = resp.json()
        assert "active" in data
        assert "count" in data

    def test_trigger_and_get_workflow(self):
        trigger_resp = client.post("/brain/workflow", json={
            "workflow_name": "full_sync",
            "data": {},
        })
        assert trigger_resp.status_code == 200
        data = trigger_resp.json()
        assert "workflow_id" in data
        assert data["name"] == "full_sync"

    def test_get_nonexistent_workflow(self):
        resp = client.get("/brain/workflows/does-not-exist-abc")
        assert resp.status_code == 404

    def test_trigger_document_intake_workflow(self):
        resp = client.post("/brain/workflow", json={
            "workflow_name": "document_intake",
            "data": {"document_id": "doc-test-001"},
        })
        assert resp.status_code == 200
        assert "workflow_id" in resp.json()


# =============================================================================
# Think & Sync
# =============================================================================

class TestBrainThinkSync:
    def test_think_empty_context(self):
        resp = client.post("/brain/think", json={"context": {}})
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    def test_think_with_context(self):
        resp = client.post("/brain/think", json={
            "context": {
                "user_id": "GUa8Km3xPq",
                "current_page": "documents",
            }
        })
        assert resp.status_code == 200

    def test_sync_all(self):
        resp = client.post("/brain/sync")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "workflow_id" in data
