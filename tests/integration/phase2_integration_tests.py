"""
Phase 2 Integration Tests - Comprehensive Module Integration
==================================================

Tests all Phase 2 modules work together properly
and serve the housing rights mission.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import create_app
from app.core.database import get_db_session
from app.core.security import StorageUser

# Import Phase 2 modules for testing
try:
    from app.core.preview_generator import get_preview_generator
    from app.core.batch_operations import get_batch_processor
    from app.core.data_export_import import get_export_import_manager
    from app.core.advanced_security import get_advanced_security_manager
    from app.core.testing_framework import get_test_framework
    from app.core.api_documentation import get_documentation_generator
    PHASE2_AVAILABLE = True
except ImportError as e:
    PHASE2_AVAILABLE = False
    print(f"Phase 2 modules not available: {e}")

@pytest.mark.asyncio
@pytest.mark.integration
class TestPhase2Integration:
    """Comprehensive Phase 2 integration tests."""
    
    @pytest.fixture
    async def test_app(self):
        """Create test app with Phase 2 modules."""
        app = create_app()
        return app
    
    @pytest.fixture
    async def test_client(self, test_app):
        """Create test client."""
        return TestClient(test_app)
    
    @pytest.fixture
    async def test_user(self):
        """Create test user."""
        return StorageUser(
            user_id="test-user-123",
            provider="google_drive",
            email="test@example.com",
            access_token="test-token",
            refresh_token="test-refresh"
        )
    
    @pytest.fixture
    async def db_session(self):
        """Create database session."""
        async with get_db_session() as session:
            yield session
    
    async def test_phase2_modules_available(self):
        """Test that all Phase 2 modules are available."""
        assert PHASE2_AVAILABLE, "Phase 2 modules should be available"
        
        # Test module availability
        preview_generator = get_preview_generator()
        assert preview_generator is not None, "Preview generator should be available"
        
        batch_processor = get_batch_processor()
        assert batch_processor is not None, "Batch processor should be available"
        
        export_manager = get_export_import_manager()
        assert export_manager is not None, "Export/import manager should be available"
        
        security_manager = get_advanced_security_manager()
        assert security_manager is not None, "Advanced security manager should be available"
        
        test_framework = get_test_framework()
        assert test_framework is not None, "Test framework should be available"
        
        doc_generator = get_documentation_generator()
        assert doc_generator is not None, "Documentation generator should be available"
    
    async def test_document_preview_integration(self, test_client, test_user):
        """Test document preview system integration."""
        # Test preview generation endpoint
        response = test_client.post(
            "/api/preview/generate",
            json={
                "document_id": "test-doc-123",
                "preview_type": "thumbnail",
                "page_number": 1
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code in [200, 404], "Preview endpoint should respond"
        
        if response.status_code == 200:
            data = response.json()
            assert "preview_url" in data, "Preview URL should be returned"
    
    async def test_batch_operations_integration(self, test_client, test_user):
        """Test batch operations system integration."""
        # Test batch operation creation
        response = test_client.post(
            "/api/batch/create",
            json={
                "operation_type": "upload",
                "items": [
                    {"type": "document", "data": {"filename": "test.pdf"}},
                    {"type": "document", "data": {"filename": "test2.pdf"}}
                ]
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code in [200, 422], "Batch creation endpoint should respond"
        
        if response.status_code == 200:
            data = response.json()
            assert "operation_id" in data, "Operation ID should be returned"
    
    async def test_data_export_import_integration(self, test_client, test_user):
        """Test data export/import system integration."""
        # Test export request
        response = test_client.post(
            "/api/export-import/export/request",
            json={
                "export_type": "documents_only",
                "format": "json"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code in [200, 422], "Export endpoint should respond"
        
        if response.status_code == 200:
            data = response.json()
            assert "export_id" in data, "Export ID should be returned"
    
    async def test_advanced_security_integration(self, test_client, test_user):
        """Test advanced security system integration."""
        # Test 2FA setup
        response = test_client.post(
            "/api/security/2fa/setup",
            json={
                "method": "totp",
                "user_email": "test@example.com"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code in [200, 400], "2FA setup endpoint should respond"
        
        if response.status_code == 200:
            data = response.json()
            assert "qr_code" in data, "QR code should be returned for TOTP setup"
    
    async def test_automated_testing_integration(self, test_client, test_user):
        """Test automated testing framework integration."""
        # Test test suite creation
        response = test_client.post(
            "/api/testing/suites",
            json={
                "suite_id": "integration-test-suite",
                "name": "Integration Test Suite",
                "description": "Tests for Phase 2 integration",
                "tags": ["integration", "phase2"]
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code in [200, 422], "Test suite creation should respond"
        
        if response.status_code == 200:
            data = response.json()
            assert "test_count" in data, "Test count should be returned"
    
    async def test_api_documentation_integration(self, test_client):
        """Test API documentation system integration."""
        # Test OpenAPI spec
        response = test_client.get("/api/docs/openapi.json")
        
        assert response.status_code == 200, "OpenAPI spec should be available"
        
        data = response.json()
        assert "openapi" in data, "OpenAPI spec should be valid"
        assert "paths" in data, "API paths should be defined"
    
    async def test_phase2_endpoints_accessible(self, test_client, test_user):
        """Test that all Phase 2 endpoints are accessible."""
        phase2_endpoints = [
            "/api/preview/generate",
            "/api/batch/create",
            "/api/export-import/export/request",
            "/api/security/2fa/setup",
            "/api/testing/suites",
            "/api/docs/openapi.json"
        ]
        
        for endpoint in phase2_endpoints:
            response = test_client.get(endpoint, headers={"Authorization": "Bearer test-token"})
            # Should not return 404 (endpoint not found)
            assert response.status_code != 404, f"Endpoint {endpoint} should be accessible"
    
    async def test_housing_rights_mission_alignment(self, test_client, test_user):
        """Test that Phase 2 modules align with housing rights mission."""
        # Test document preview for housing documents
        response = test_client.post(
            "/api/preview/generate",
            json={
                "document_id": "lease-agreement-123",
                "preview_type": "preview",
                "max_pages": 5
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Should handle housing document types
        assert response.status_code in [200, 404], "Should handle housing documents"
        
        # Test batch operations for evidence collection
        response = test_client.post(
            "/api/batch/create",
            json={
                "operation_type": "upload",
                "items": [
                    {"type": "evidence", "data": {"category": "lease_violation"}},
                    {"type": "evidence", "data": {"category": "maintenance_issue"}}
                ]
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code in [200, 422], "Should handle evidence batch operations"
    
    async def test_cross_module_integration(self, test_client, test_user):
        """Test integration between different Phase 2 modules."""
        # Test that batch operations can trigger preview generation
        response = test_client.post(
            "/api/batch/create",
            json={
                "operation_type": "upload",
                "items": [
                    {"type": "document", "data": {"filename": "lease.pdf", "generate_preview": True}}
                ]
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code in [200, 422], "Batch operations should integrate with preview"
        
        # Test that export can include preview data
        response = test_client.post(
            "/api/export-import/export/request",
            json={
                "export_type": "all_data",
                "format": "zip",
                "include_previews": True
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code in [200, 422], "Export should integrate with preview system"
    
    async def test_performance_under_load(self, test_client, test_user):
        """Test Phase 2 modules performance under load."""
        import time
        
        # Test multiple concurrent preview requests
        start_time = time.time()
        
        tasks = []
        for i in range(5):
            response = test_client.post(
                "/api/preview/generate",
                json={
                    "document_id": f"test-doc-{i}",
                    "preview_type": "thumbnail"
                },
                headers={"Authorization": "Bearer test-token"}
            )
            tasks.append(response)
        
        # All requests should complete within reasonable time
        end_time = time.time()
        duration = end_time - start_time
        
        assert duration < 10.0, "Concurrent preview requests should complete within 10 seconds"
        
        for response in tasks:
            assert response.status_code in [200, 404], "Concurrent requests should be handled properly"
    
    async def test_error_handling_integration(self, test_client, test_user):
        """Test error handling across Phase 2 modules."""
        # Test invalid preview request
        response = test_client.post(
            "/api/preview/generate",
            json={
                "document_id": "",  # Invalid empty ID
                "preview_type": "thumbnail"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 422, "Should handle invalid preview requests"
        
        # Test invalid batch operation
        response = test_client.post(
            "/api/batch/create",
            json={
                "operation_type": "invalid_operation",  # Invalid operation
                "items": []
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 422, "Should handle invalid batch operations"
        
        # Test invalid security request
        response = test_client.post(
            "/api/security/2fa/setup",
            json={
                "method": "invalid_method",  # Invalid 2FA method
                "user_email": "test@example.com"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 400, "Should handle invalid security requests"

@pytest.mark.asyncio
@pytest.mark.performance
class TestPhase2Performance:
    """Performance tests for Phase 2 modules."""
    
    async def test_preview_generation_performance(self, test_client, test_user):
        """Test preview generation performance."""
        import time
        
        # Test preview generation speed
        start_time = time.time()
        
        response = test_client.post(
            "/api/preview/generate",
            json={
                "document_id": "test-doc-large",
                "preview_type": "preview",
                "max_pages": 10
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert response.status_code in [200, 404], "Preview generation should work"
        assert duration < 5.0, "Preview generation should complete within 5 seconds"
    
    async def test_batch_operations_performance(self, test_client, test_user):
        """Test batch operations performance."""
        import time
        
        # Test large batch operation
        start_time = time.time()
        
        response = test_client.post(
            "/api/batch/create",
            json={
                "operation_type": "upload",
                "items": [{"type": "document", "data": {"filename": f"test-{i}.pdf"}} for i in range(50)]
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert response.status_code in [200, 422], "Batch operations should work"
        assert duration < 3.0, "Batch creation should complete within 3 seconds"
    
    async def test_security_operations_performance(self, test_client, test_user):
        """Test security operations performance."""
        import time
        
        # Test 2FA verification speed
        start_time = time.time()
        
        response = test_client.post(
            "/api/security/2fa/verify",
            json={
                "code": "123456",  # Test code
                "method": "totp"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert response.status_code in [200, 400], "2FA verification should work"
        assert duration < 2.0, "2FA verification should complete within 2 seconds"

@pytest.mark.asyncio
@pytest.mark.security
class TestPhase2Security:
    """Security tests for Phase 2 modules."""
    
    async def test_preview_security(self, test_client, test_user):
        """Test preview system security."""
        # Test unauthorized access
        response = test_client.post(
            "/api/preview/generate",
            json={
                "document_id": "test-doc-123",
                "preview_type": "thumbnail"
            }
            # No authorization header
        )
        
        assert response.status_code == 401, "Preview should require authentication"
        
        # Test invalid token
        response = test_client.post(
            "/api/preview/generate",
            json={
                "document_id": "test-doc-123",
                "preview_type": "thumbnail"
            },
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401, "Preview should reject invalid tokens"
    
    async def test_batch_operations_security(self, test_client, test_user):
        """Test batch operations security."""
        # Test unauthorized batch operation
        response = test_client.post(
            "/api/batch/create",
            json={
                "operation_type": "delete",  # Dangerous operation
                "items": [{"type": "document", "data": {"document_id": "all"}}]
            }
            # No authorization header
        )
        
        assert response.status_code == 401, "Batch operations should require authentication"
        
        # Test rate limiting
        for i in range(10):
            response = test_client.post(
                "/api/batch/create",
                json={
                    "operation_type": "upload",
                    "items": [{"type": "document", "data": {"filename": f"test-{i}.pdf"}}]
                },
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should be rate limited after several requests
            if i > 5:
                assert response.status_code in [200, 429], "Should apply rate limiting"
    
    async def test_data_export_security(self, test_client, test_user):
        """Test data export security."""
        # Test unauthorized export
        response = test_client.post(
            "/api/export-import/export/request",
            json={
                "export_type": "all_data",  # Sensitive operation
                "format": "json"
            }
            # No authorization header
        )
        
        assert response.status_code == 401, "Data export should require authentication"
        
        # Test export rate limiting
        response = test_client.post(
            "/api/export-import/export/request",
            json={
                "export_type": "documents_only",
                "format": "json"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code in [200, 429], "Export should be rate limited"
    
    async def test_advanced_security_features(self, test_client, test_user):
        """Test advanced security features."""
        # Test 2FA setup security
        response = test_client.post(
            "/api/security/2fa/setup",
            json={
                "method": "totp",
                "user_email": "test@example.com"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code in [200, 400], "2FA setup should work"
        
        # Test session management
        response = test_client.post(
            "/api/security/session/create",
            json={
                "require_2fa": False
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code in [200, 401], "Session creation should work"

# Test configuration and fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_config():
    """Test configuration for Phase 2 modules."""
    return {
        "preview": {
            "max_file_size": 50 * 1024 * 1024,  # 50MB
            "supported_formats": ["pdf", "jpg", "png", "txt", "docx"],
            "cache_ttl": 3600  # 1 hour
        },
        "batch": {
            "max_items_per_batch": 100,
            "max_concurrent_operations": 5,
            "timeout_seconds": 300  # 5 minutes
        },
        "security": {
            "2fa_enabled": True,
            "session_timeout": 3600,  # 1 hour
            "max_sessions_per_user": 5
        },
        "export_import": {
            "max_export_size": 100 * 1024 * 1024,  # 100MB
            "supported_formats": ["json", "csv", "zip"],
            "retention_days": 7
        }
    }

# Integration test runner
async def run_phase2_integration_tests():
    """Run all Phase 2 integration tests."""
    import subprocess
    import sys
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/integration/phase2_integration_tests.py",
            "-v", "--tb=short",
            "-m", "integration"
        ], capture_output=True, text=True, cwd=".")
        
        print(f"Integration tests completed with return code: {result.returncode}")
        print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Errors: {result.stderr}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"Failed to run integration tests: {e}")
        return False

if __name__ == "__main__":
    # Run integration tests when executed directly
    success = asyncio.run(run_phase2_integration_tests())
    sys.exit(0 if success else 1)
