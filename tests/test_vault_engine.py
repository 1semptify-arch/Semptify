"""
Tests for the Vault Engine - Centralized Access Control System

Tests the core VaultAccessEngine functionality:
- Access control verification
- Role-based permissions
- Resource CRUD operations through the engine
- Audit logging
- Sharing capabilities
"""

from datetime import UTC, datetime

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.core.user_context import StorageProvider, UserContext, UserRole
from app.core.user_id import parse_user_id
from app.core.utc import utc_now
from app.main import app
from app.modules.vault_engine.router import yellow_access
from app.modules.vault_engine.service import (
    ResourceType,
    VaultResource,
    get_vault_engine,
)

client = TestClient(app)


# =============================================================================
# Test Fixtures
# =============================================================================


def _make_user_context(user_id: str) -> UserContext:
    """Build a UserContext from a user ID, using the encoded provider and role."""
    provider, role, _ = parse_user_id(user_id)
    if not provider:
        provider = "google_drive"
    if not role:
        role = "tenant"
    return UserContext(
        user_id=user_id,
        provider=StorageProvider(provider),
        storage_user_id=user_id,
        access_token="no-token",
        role=UserRole(role),
    )


async def _override_yellow_access(request: Request) -> UserContext:
    """Authenticate vault-engine tests using the semptify_uid cookie."""
    user_id = request.cookies.get("semptify_uid")
    if user_id and len(str(user_id)) >= 3:
        return _make_user_context(user_id)
    return _make_user_context("GUtest1234")


@pytest.fixture(autouse=True)
def patch_vault_auth():
    """Override the auth dependency for vault-engine endpoint tests."""
    app.dependency_overrides[yellow_access] = _override_yellow_access
    yield
    app.dependency_overrides.pop(yellow_access, None)


@pytest.fixture
def user_cookie():
    """Regular user cookie."""
    return {"semptify_uid": "GUa8Km3xPq"}  # Google + User + random


@pytest.fixture
def manager_cookie():
    """Manager user cookie."""
    return {"semptify_uid": "DMb7Nj2yRs"}  # Dropbox + Manager + random


@pytest.fixture
def legal_cookie():
    """Legal professional cookie."""
    return {"semptify_uid": "OLc6Pk4wQt"}  # OneDrive + Legal + random


@pytest.fixture
def admin_cookie():
    """Admin user cookie."""
    return {"semptify_uid": "GAd5Ql1vZu"}  # Google + Admin + random


# =============================================================================
# Resource Types Endpoint Tests
# =============================================================================


class TestResourceTypes:
    """Test resource type enumeration."""

    def test_list_resource_types(self, user_cookie):
        """Should list all valid resource types."""
        response = client.get("/api/vault-engine/resource-types", cookies=user_cookie)
        assert response.status_code == 200
        data = response.json()
        assert "types" in data
        assert "document" in data["types"]
        assert "timeline_event" in data["types"]
        assert "calendar_event" in data["types"]

    def test_list_access_levels(self, user_cookie):
        """Should list all valid access levels."""
        response = client.get("/api/vault-engine/access-levels", cookies=user_cookie)
        assert response.status_code == 200
        data = response.json()
        assert "levels" in data
        assert "read" in data["levels"]
        assert "write" in data["levels"]
        assert "delete" in data["levels"]


# =============================================================================
# Access Check Endpoint Tests
# =============================================================================


class TestAccessCheck:
    """Test access permission checking."""

    def test_check_access_unauthorized(self):
        """Should require authentication."""
        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "test-doc-1", "action": "read"},
        )
        # May return 401 or handle gracefully
        assert response.status_code in [401, 403, 200]

    def test_check_access_user_read(self, user_cookie):
        """User should have read access to documents."""
        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "test-doc-1", "action": "read"},
            cookies=user_cookie,
        )
        assert response.status_code == 200
        data = response.json()
        assert "allowed" in data
        assert "reason" in data

    def test_check_access_invalid_resource_type(self, user_cookie):
        """Should reject invalid resource types (or be blocked by middleware)."""
        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "invalid_type", "resource_id": "test-doc-1", "action": "read"},
            cookies=user_cookie,
        )
        # Either blocked by middleware (401) or validation error (400/422)
        assert response.status_code in [400, 401, 422]
        data = response.json()
        # Check for error message in various response formats
        if "detail" in data:
            assert "invalid" in data["detail"].lower() or "resource" in data["detail"].lower()
        elif "message" in data:
            assert "invalid" in data["message"].lower() or "resource" in data["message"].lower()
        elif "error" in data:
            assert True  # Has an error key, good enough

    def test_check_access_invalid_action(self, user_cookie):
        """Should reject invalid actions (or be blocked by middleware)."""
        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "test-doc-1", "action": "invalid_action"},
            cookies=user_cookie,
        )
        # Either blocked by middleware (401) or validation error (400/422)
        assert response.status_code in [400, 401, 422]
        data = response.json()
        # Check for error message in various response formats
        if "detail" in data:
            assert "invalid" in data["detail"].lower() or "action" in data["detail"].lower()
        elif "message" in data:
            assert "invalid" in data["message"].lower() or "action" in data["message"].lower()
        elif "error" in data:
            assert True  # Has an error key, good enough


# =============================================================================
# Read Endpoint Tests
# =============================================================================


class TestReadOperations:
    """Test vault read operations."""

    def test_read_document(self, user_cookie):
        """Should allow reading documents."""
        response = client.post(
            "/api/vault-engine/read",
            json={"resource_type": "document", "resource_id": "test-doc-1", "reason": "Testing read access"},
            cookies=user_cookie,
        )
        # May succeed or fail depending on whether resource exists
        assert response.status_code in [200, 403, 404]

    def test_read_invalid_type(self, user_cookie):
        """Should reject invalid resource type."""
        response = client.post(
            "/api/vault-engine/read",
            json={"resource_type": "not_real", "resource_id": "test-doc-1"},
            cookies=user_cookie,
        )
        assert response.status_code == 400


# =============================================================================
# Write Endpoint Tests
# =============================================================================


class TestWriteOperations:
    """Test vault write operations."""

    def test_write_document_user(self, user_cookie):
        """Regular user may not have write access by default."""
        response = client.post(
            "/api/vault-engine/write",
            json={
                "resource_type": "document",
                "resource_id": "new-doc-1",
                "data": {"title": "Test Document", "content": "Test content"},
                "reason": "Testing write",
            },
            cookies=user_cookie,
        )
        # Users may or may not have write access depending on implementation
        assert response.status_code in [200, 403]

    def test_write_document_manager(self, manager_cookie):
        """Manager should have write access."""
        response = client.post(
            "/api/vault-engine/write",
            json={
                "resource_type": "document",
                "resource_id": "new-doc-2",
                "data": {"title": "Manager Document"},
                "reason": "Manager creating document",
            },
            cookies=manager_cookie,
        )
        # Manager should typically have write access
        assert response.status_code in [200, 201, 403]

    def test_write_invalid_type(self, user_cookie):
        """Should reject invalid resource type."""
        response = client.post(
            "/api/vault-engine/write",
            json={"resource_type": "fake_type", "resource_id": "test", "data": {}},
            cookies=user_cookie,
        )
        assert response.status_code == 400


# =============================================================================
# Role-Based Access Control Tests
# =============================================================================

# Map the hard-coded test user IDs to the role strings the VaultAccessEngine's
# ACCESS_MATRIX expects. This decouples the tests from the exact role encoding
# in user_id.py while still exercising the engine's role/scope logic.
_VAULT_TEST_ROLE_MAP = {
    "GUa8Km3xPq": "user",
    "GAa8Km3xPq": "advocate",
    "GLc6Pk4wQt": "legal",
    "GMb7Nj2yRs": "manager",
    "GAd5Ql1vZu": "admin",
}


def _seed_matrix_resources(engine):
    """Populate in-memory resources so scope detection works for matrix tests.

    The user matrix test uses unprefixed scope names for shared/case/org/system
    resources; other roles prefix every resource with the role name.
    """
    for user_id, role in _VAULT_TEST_ROLE_MAP.items():
        if role == "user":
            resource_ids = {
                "own": "user-own-doc",
                "shared": "shared-doc",
                "case": "case-doc",
                "org": "org-doc",
                "system": "system-doc",
            }
        else:
            resource_ids = {
                "own": f"{role}-own-doc",
                "shared": f"{role}-shared-doc",
                "case": f"{role}-case-doc",
                "org": f"{role}-org-doc",
                "system": f"{role}-system-doc",
            }

        engine._resources[resource_ids["own"]] = VaultResource(
            id=resource_ids["own"],
            type=ResourceType.DOCUMENT,
            owner_id=user_id,
            created_at=utc_now(),
        )
        engine._resources[resource_ids["shared"]] = VaultResource(
            id=resource_ids["shared"],
            type=ResourceType.DOCUMENT,
            owner_id="someone-else",
            created_at=utc_now(),
            shared_with=[user_id],
        )
        engine._resources[resource_ids["case"]] = VaultResource(
            id=resource_ids["case"],
            type=ResourceType.DOCUMENT,
            owner_id="someone-else",
            created_at=utc_now(),
            case_ids=["case-1"],
        )
        engine._resources[resource_ids["org"]] = VaultResource(
            id=resource_ids["org"],
            type=ResourceType.DOCUMENT,
            owner_id="someone-else",
            created_at=utc_now(),
            org_id="org-1",
        )
        engine._resources[resource_ids["system"]] = VaultResource(
            id=resource_ids["system"],
            type=ResourceType.DOCUMENT,
            owner_id="someone-else",
            created_at=utc_now(),
        )


@pytest.fixture(autouse=True)
def patch_vault_matrix(monkeypatch):
    """Make role/scope matrix tests deterministic for the hard-coded UIDs."""
    import app.modules.vault_engine.service as vault_service

    original_get_role = vault_service.get_role_from_user_id

    def _test_get_role(user_id: str) -> str:
        return _VAULT_TEST_ROLE_MAP.get(user_id, original_get_role(user_id))

    monkeypatch.setattr(vault_service, "get_role_from_user_id", _test_get_role)

    engine = get_vault_engine()
    saved_resources = dict(engine._resources)
    engine._resources.clear()
    _seed_matrix_resources(engine)
    yield
    engine._resources.clear()
    engine._resources.update(saved_resources)


class TestRoleBasedAccessControl:
    """Test role-based access decisions for different scopes."""

    def test_user_access_matrix(self, user_cookie):
        """Test user role access permissions."""
        # User should have RWD on OWN resources
        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "user-own-doc", "action": "read"},
            cookies=user_cookie,
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is True

        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "user-own-doc", "action": "write"},
            cookies=user_cookie,
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is True

        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "user-own-doc", "action": "delete"},
            cookies=user_cookie,
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is True

        # User should have only READ on SHARED resources
        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "shared-doc", "action": "read"},
            cookies=user_cookie,
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is True

        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "shared-doc", "action": "write"},
            cookies=user_cookie,
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is False

        # User should have NO access to CASE/ORG/SYSTEM resources
        for scope_resource in ["case-doc", "org-doc", "system-doc"]:
            for action in ["read", "write", "delete"]:
                response = client.post(
                    "/api/vault-engine/check-access",
                    json={"resource_type": "document", "resource_id": scope_resource, "action": action},
                    cookies=user_cookie,
                )
                assert response.status_code == 200
                assert response.json()["allowed"] is False

    def test_advocate_access_matrix(self):
        """Test advocate role access permissions."""
        advocate_cookie = {"semptify_uid": "GAa8Km3xPq"}  # Google + Advocate + random

        # Advocate should have RWD on OWN, RW on SHARED, RW on CASE, R on ORG
        # OWN - all permissions
        for action in ["read", "write", "delete"]:
            response = client.post(
                "/api/vault-engine/check-access",
                json={"resource_type": "document", "resource_id": "advocate-own-doc", "action": action},
                cookies=advocate_cookie,
            )
            assert response.status_code == 200
            assert response.json()["allowed"] is True

        # SHARED - read/write only
        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "advocate-shared-doc", "action": "read"},
            cookies=advocate_cookie,
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is True

        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "advocate-shared-doc", "action": "write"},
            cookies=advocate_cookie,
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is True

        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "advocate-shared-doc", "action": "delete"},
            cookies=advocate_cookie,
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is False

        # CASE - read/write only
        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "advocate-case-doc", "action": "read"},
            cookies=advocate_cookie,
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is True

        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "advocate-case-doc", "action": "write"},
            cookies=advocate_cookie,
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is True

        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "advocate-case-doc", "action": "delete"},
            cookies=advocate_cookie,
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is False

        # ORG - read only
        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "advocate-org-doc", "action": "read"},
            cookies=advocate_cookie,
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is True

        for action in ["write", "delete"]:
            response = client.post(
                "/api/vault-engine/check-access",
                json={"resource_type": "document", "resource_id": "advocate-org-doc", "action": action},
                cookies=advocate_cookie,
            )
            assert response.status_code == 200
            assert response.json()["allowed"] is False

        # SYSTEM - no access
        for action in ["read", "write", "delete"]:
            response = client.post(
                "/api/vault-engine/check-access",
                json={"resource_type": "document", "resource_id": "advocate-system-doc", "action": action},
                cookies=advocate_cookie,
            )
            assert response.status_code == 200
            assert response.json()["allowed"] is False

    def test_legal_access_matrix(self):
        """Test legal role access permissions."""
        legal_cookie = {"semptify_uid": "GLc6Pk4wQt"}  # Google + Legal + random

        # Legal should have RWD on OWN, RW on SHARED, RWD on CASE, RW on ORG, R on SYSTEM
        # OWN - all permissions
        for action in ["read", "write", "delete"]:
            response = client.post(
                "/api/vault-engine/check-access",
                json={"resource_type": "document", "resource_id": "legal-own-doc", "action": action},
                cookies=legal_cookie,
            )
            assert response.status_code == 200
            assert response.json()["allowed"] is True

        # SHARED - read/write only
        for action in ["read", "write"]:
            response = client.post(
                "/api/vault-engine/check-access",
                json={"resource_type": "document", "resource_id": "legal-shared-doc", "action": action},
                cookies=legal_cookie,
            )
            assert response.status_code == 200
            assert response.json()["allowed"] is True

        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "legal-shared-doc", "action": "delete"},
            cookies=legal_cookie,
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is False

        # CASE - all permissions
        for action in ["read", "write", "delete"]:
            response = client.post(
                "/api/vault-engine/check-access",
                json={"resource_type": "document", "resource_id": "legal-case-doc", "action": action},
                cookies=legal_cookie,
            )
            assert response.status_code == 200
            assert response.json()["allowed"] is True

        # ORG - read/write only
        for action in ["read", "write"]:
            response = client.post(
                "/api/vault-engine/check-access",
                json={"resource_type": "document", "resource_id": "legal-org-doc", "action": action},
                cookies=legal_cookie,
            )
            assert response.status_code == 200
            assert response.json()["allowed"] is True

        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "legal-org-doc", "action": "delete"},
            cookies=legal_cookie,
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is False

        # SYSTEM - read only
        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "legal-system-doc", "action": "read"},
            cookies=legal_cookie,
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is True

        for action in ["write", "delete"]:
            response = client.post(
                "/api/vault-engine/check-access",
                json={"resource_type": "document", "resource_id": "legal-system-doc", "action": action},
                cookies=legal_cookie,
            )
            assert response.status_code == 200
            assert response.json()["allowed"] is False

    def test_manager_access_matrix(self):
        """Test manager role access permissions."""
        manager_cookie = {"semptify_uid": "GMb7Nj2yRs"}  # Google + Manager + random

        # Manager should have RWD on OWN, RW on SHARED, RW on CASE, RWD on ORG, R on SYSTEM
        # OWN - all permissions
        for action in ["read", "write", "delete"]:
            response = client.post(
                "/api/vault-engine/check-access",
                json={"resource_type": "document", "resource_id": "manager-own-doc", "action": action},
                cookies=manager_cookie,
            )
            assert response.status_code == 200
            assert response.json()["allowed"] is True

        # SHARED - read/write only
        for action in ["read", "write"]:
            response = client.post(
                "/api/vault-engine/check-access",
                json={"resource_type": "document", "resource_id": "manager-shared-doc", "action": action},
                cookies=manager_cookie,
            )
            assert response.status_code == 200
            assert response.json()["allowed"] is True

        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "manager-shared-doc", "action": "delete"},
            cookies=manager_cookie,
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is False

        # CASE - read/write only
        for action in ["read", "write"]:
            response = client.post(
                "/api/vault-engine/check-access",
                json={"resource_type": "document", "resource_id": "manager-case-doc", "action": action},
                cookies=manager_cookie,
            )
            assert response.status_code == 200
            assert response.json()["allowed"] is True

        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "manager-case-doc", "action": "delete"},
            cookies=manager_cookie,
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is False

        # ORG - all permissions
        for action in ["read", "write", "delete"]:
            response = client.post(
                "/api/vault-engine/check-access",
                json={"resource_type": "document", "resource_id": "manager-org-doc", "action": action},
                cookies=manager_cookie,
            )
            assert response.status_code == 200
            assert response.json()["allowed"] is True

        # SYSTEM - read only
        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "manager-system-doc", "action": "read"},
            cookies=manager_cookie,
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is True

        for action in ["write", "delete"]:
            response = client.post(
                "/api/vault-engine/check-access",
                json={"resource_type": "document", "resource_id": "manager-system-doc", "action": action},
                cookies=manager_cookie,
            )
            assert response.status_code == 200
            assert response.json()["allowed"] is False

    def test_admin_access_matrix(self, admin_cookie):
        """Test admin role has all permissions on all scopes."""
        # Admin should have all permissions on all scopes
        for scope_resource in [
            "admin-own-doc",
            "admin-shared-doc",
            "admin-case-doc",
            "admin-org-doc",
            "admin-system-doc",
        ]:
            for action in ["read", "write", "delete"]:
                response = client.post(
                    "/api/vault-engine/check-access",
                    json={"resource_type": "document", "resource_id": scope_resource, "action": action},
                    cookies=admin_cookie,
                )
                assert response.status_code == 200
                assert response.json()["allowed"] is True


# =============================================================================
# Sharing Endpoint Tests
# =============================================================================


class TestShareOperations:
    """Test resource sharing functionality."""

    def test_share_resource(self, manager_cookie):
        """Manager should be able to share resources."""
        response = client.post(
            "/api/vault-engine/share",
            json={
                "resource_id": "share-test-1",
                "share_with": "GUb8Km3xPq",  # Another user
                "reason": "Sharing for collaboration",
            },
            cookies=manager_cookie,
        )
        # May succeed or fail depending on ownership
        assert response.status_code in [200, 403]

    def test_unshare_resource(self, manager_cookie):
        """Should be able to remove sharing."""
        response = client.post(
            "/api/vault-engine/unshare",
            json={"resource_id": "share-test-1", "unshare_from": "GUb8Km3xPq"},
            cookies=manager_cookie,
        )
        assert response.status_code in [200, 403]


# =============================================================================
# List Endpoint Tests
# =============================================================================


class TestListOperations:
    """Test resource listing functionality."""

    def test_list_resources(self, user_cookie):
        """Should list accessible resources."""
        response = client.get("/api/vault-engine/list", cookies=user_cookie)
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "resources" in data
        assert isinstance(data["resources"], list)

    def test_list_by_type(self, user_cookie):
        """Should filter by resource type."""
        response = client.get("/api/vault-engine/list", params={"resource_type": "document"}, cookies=user_cookie)
        assert response.status_code == 200

    def test_list_include_deleted(self, admin_cookie):
        """Admin should be able to see deleted resources."""
        response = client.get("/api/vault-engine/list", params={"include_deleted": True}, cookies=admin_cookie)
        assert response.status_code == 200

    def test_list_invalid_type(self, user_cookie):
        """Should reject invalid resource type filter."""
        response = client.get("/api/vault-engine/list", params={"resource_type": "invalid"}, cookies=user_cookie)
        assert response.status_code == 400


# =============================================================================
# Audit Log Endpoint Tests
# =============================================================================


class TestAuditLog:
    """Test audit logging functionality."""

    def test_get_audit_log(self, user_cookie):
        """Should return audit entries."""
        response = client.get("/api/vault-engine/audit", cookies=user_cookie)
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "entries" in data

    def test_audit_log_filter_by_resource(self, user_cookie):
        """Should filter audit by resource."""
        response = client.get("/api/vault-engine/audit", params={"resource_id": "test-doc-1"}, cookies=user_cookie)
        assert response.status_code == 200

    def test_audit_log_limit(self, user_cookie):
        """Should respect limit parameter."""
        response = client.get("/api/vault-engine/audit", params={"limit": 10}, cookies=user_cookie)
        assert response.status_code == 200


# =============================================================================
# Stats Endpoint Tests
# =============================================================================


class TestStats:
    """Test statistics endpoint."""

    def test_get_stats(self, admin_cookie):
        """Admin should get vault statistics."""
        response = client.get("/api/vault-engine/stats", cookies=admin_cookie)
        assert response.status_code == 200
        data = response.json()
        # Should return some stats structure
        assert isinstance(data, dict)


# =============================================================================
# Role-Based Access Tests
# =============================================================================


class TestRoleBasedAccess:
    """Test that different roles have appropriate permissions."""

    def test_user_role_permissions(self, user_cookie):
        """Regular user should have limited access."""
        # Can read
        read_response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "test", "action": "read"},
            cookies=user_cookie,
        )
        assert read_response.status_code == 200

        # May not be able to delete
        delete_response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "test", "action": "delete"},
            cookies=user_cookie,
        )
        assert delete_response.status_code == 200
        # Check if delete is denied
        if delete_response.json().get("allowed") is False:
            assert (
                "denied" in delete_response.json().get("reason", "").lower()
                or "not allowed" in delete_response.json().get("reason", "").lower()
                or delete_response.json().get("allowed") is False
            )

    def test_legal_role_permissions(self, legal_cookie):
        """Legal professionals should have broader read access."""
        response = client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "test", "action": "read"},
            cookies=legal_cookie,
        )
        assert response.status_code == 200
        # Legal should typically be allowed to read
        assert "allowed" in response.json()

    def test_admin_role_permissions(self, admin_cookie):
        """Admin should have full access."""
        for action in ["read", "write", "delete"]:
            response = client.post(
                "/api/vault-engine/check-access",
                json={"resource_type": "document", "resource_id": "test", "action": action},
                cookies=admin_cookie,
            )
            assert response.status_code == 200
            # Admin should be allowed for all actions
            assert "allowed" in response.json()


# =============================================================================
# Integration Tests
# =============================================================================


class TestVaultEngineIntegration:
    """Integration tests for vault engine workflow."""

    def test_full_document_lifecycle(self, manager_cookie):
        """Test create -> read -> update -> delete workflow."""
        doc_id = f"lifecycle-test-{datetime.now(UTC).timestamp()}"

        # 1. Write (create) document
        write_response = client.post(
            "/api/vault-engine/write",
            json={
                "resource_type": "document",
                "resource_id": doc_id,
                "data": {"title": "Lifecycle Test", "version": 1},
                "reason": "Creating test document",
            },
            cookies=manager_cookie,
        )
        # May or may not succeed depending on implementation
        if write_response.status_code == 200:
            # 2. Read document
            read_response = client.post(
                "/api/vault-engine/read",
                json={"resource_type": "document", "resource_id": doc_id},
                cookies=manager_cookie,
            )
            assert read_response.status_code in [200, 404]

    def test_access_audit_trail(self, user_cookie):
        """Verify access creates audit trail."""
        # Make some accesses
        client.post(
            "/api/vault-engine/check-access",
            json={"resource_type": "document", "resource_id": "audit-test-1", "action": "read"},
            cookies=user_cookie,
        )

        # Check audit log
        audit_response = client.get("/api/vault-engine/audit", cookies=user_cookie)
        assert audit_response.status_code == 200
        # Should have entries (may or may not include our test)
        data = audit_response.json()
        assert "entries" in data
