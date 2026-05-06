"""
MNDES Exhibit Service Unit Tests
================================

Tests for the Minnesota Digital Exhibit System service.
Covers package creation, attestations, compliance checks, and database persistence.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.mndes_exhibit_service import MNDESExhibitService, mndes_exhibit_service
from app.models.mndes_exhibit import (
    MNDESExhibit,
    MNDESExhibitCategory,
    MNDESExhibitPackage,
    MNDESExhibitStatus,
    MNDESCaseType,
    MNDESPackageCreateRequest,
    MNDESAttestationRequest,
    MNDESSubmissionConfirmRequest,
)
from app.models.models import MNDESExhibitPackageDB, MNDESExhibitItemDB


@pytest.fixture
def service():
    """Create a fresh service instance for each test."""
    return MNDESExhibitService()


@pytest.fixture
def sample_vault_docs():
    """Sample vault documents for testing."""
    return [
        {
            "vault_id": "vault_doc_001",
            "filename": "lease_agreement.pdf",
            "file_size_bytes": 1024 * 1024,  # 1MB
        },
        {
            "vault_id": "vault_doc_002",
            "filename": "notice_to_vacate.pdf",
            "file_size_bytes": 512 * 1024,  # 512KB
        },
        {
            "vault_id": "vault_doc_003",
            "filename": "receipt.jpg",
            "file_size_bytes": 2 * 1024 * 1024,  # 2MB
        },
    ]


@pytest.fixture
def create_request(sample_vault_docs):
    """Sample package creation request."""
    return MNDESPackageCreateRequest(
        vault_ids=[doc["vault_id"] for doc in sample_vault_docs],
        mn_case_number="19AV-CV-2024-1234",
        case_type=MNDESCaseType.EVICTION,
        exhibit_names={
            "vault_doc_001": "Lease Agreement (Exhibit A)",
            "vault_doc_002": "Notice to Vacate (Exhibit B)",
        },
        no_contact_order=False,
        is_sealed_case=False,
    )


class TestPackageCreation:
    """Test package creation functionality."""

    @pytest.mark.asyncio
    async def test_create_package_success(self, service, create_request, sample_vault_docs):
        """Test successful package creation."""
        with patch.object(service, '_save_package_to_db', new_callable=AsyncMock) as mock_save:
            package = await service.create_package(
                request=create_request,
                vault_docs=sample_vault_docs,
                user_id="user_123",
            )
            
            assert package is not None
            assert package.mn_case_number == "19AV-CV-2024-1234"
            assert package.case_type == MNDESCaseType.EVICTION
            assert len(package.exhibits) == 3
            assert package.user_id == "user_123"
            
            # Check that package was saved to DB
            mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_package_missing_vault_doc(self, service, create_request):
        """Test package creation with missing vault document."""
        # Remove one vault doc from the list
        incomplete_docs = [
            {"vault_id": "vault_doc_001", "filename": "lease.pdf", "file_size_bytes": 1024}
        ]
        
        with patch.object(service, '_save_package_to_db', new_callable=AsyncMock):
            package = await service.create_package(
                request=create_request,  # Asks for 3 docs
                vault_docs=incomplete_docs,  # Only provides 1
                user_id="user_123",
            )
            
            # Should only create exhibits for available docs
            assert len(package.exhibits) == 1
    
    @pytest.mark.asyncio
    async def test_create_package_sealed_case_warning(self, service, create_request, sample_vault_docs):
        """Test that sealed cases generate warnings."""
        create_request.is_sealed_case = True
        
        with patch.object(service, '_save_package_to_db', new_callable=AsyncMock):
            with patch('app.services.mndes_exhibit_service.logger') as mock_logger:
                await service.create_package(
                    request=create_request,
                    vault_docs=sample_vault_docs,
                    user_id="user_123",
                )
                
                mock_logger.warning.assert_called_once()
                assert "sealed case" in mock_logger.warning.call_args[0][0].lower()


class TestAttestations:
    """Test attestation functionality."""

    @pytest.mark.asyncio
    async def test_apply_attestations_success(self, service, create_request, sample_vault_docs):
        """Test successful attestation application."""
        with patch.object(service, '_save_package_to_db', new_callable=AsyncMock):
            # Create package first
            package = await service.create_package(
                request=create_request,
                vault_docs=sample_vault_docs,
                user_id="user_123",
            )
            
            # Mock getting package from DB
            with patch.object(service, 'get_package', new_callable=AsyncMock, return_value=package):
                attestation_request = MNDESAttestationRequest(
                    package_id=package.package_id,
                    attests_no_sexual_content=True,
                    attests_not_discovery=True,
                    attests_not_motion_attachment=True,
                    attests_understands_no_return=True,
                    attests_semptify_not_mndes=True,
                    attested_by="John Doe",
                )
                
                updated_package = await service.apply_attestations(attestation_request)
                
                assert updated_package.checklist_complete is True
                assert updated_package.exhibits[0].user_attested_no_sexual_content is True
    
    @pytest.mark.asyncio
    async def test_apply_attestations_incomplete(self, service, create_request, sample_vault_docs):
        """Test attestation with incomplete checklist."""
        with patch.object(service, '_save_package_to_db', new_callable=AsyncMock):
            package = await service.create_package(
                request=create_request,
                vault_docs=sample_vault_docs,
                user_id="user_123",
            )
            
            with patch.object(service, 'get_package', new_callable=AsyncMock, return_value=package):
                attestation_request = MNDESAttestationRequest(
                    package_id=package.package_id,
                    attests_no_sexual_content=True,
                    attests_not_discovery=False,  # Missing this one
                    attests_not_motion_attachment=True,
                    attests_understands_no_return=True,
                    attests_semptify_not_mndes=True,
                )
                
                updated_package = await service.apply_attestations(attestation_request)
                
                assert updated_package.checklist_complete is False
    
    @pytest.mark.asyncio
    async def test_apply_attestations_package_not_found(self, service):
        """Test attestation with non-existent package."""
        with patch.object(service, 'get_package', new_callable=AsyncMock, return_value=None):
            attestation_request = MNDESAttestationRequest(
                package_id="nonexistent_package",
                attests_no_sexual_content=True,
                attests_not_discovery=True,
                attests_not_motion_attachment=True,
                attests_understands_no_return=True,
                attests_semptify_not_mndes=True,
            )
            
            with pytest.raises(ValueError, match="Package nonexistent_package not found"):
                await service.apply_attestations(attestation_request)


class TestSubmissionConfirmation:
    """Test submission confirmation functionality."""

    @pytest.mark.asyncio
    async def test_confirm_submission_success(self, service, create_request, sample_vault_docs):
        """Test successful submission confirmation."""
        with patch.object(service, '_save_package_to_db', new_callable=AsyncMock):
            package = await service.create_package(
                request=create_request,
                vault_docs=sample_vault_docs,
                user_id="user_123",
            )
            
            with patch.object(service, 'get_package', new_callable=AsyncMock, return_value=package):
                confirm_request = MNDESSubmissionConfirmRequest(
                    package_id=package.package_id,
                    exhibit_id=package.exhibits[0].exhibit_id,
                    mndes_tracking_number="MN123456789",
                    submitted_at=datetime.now(timezone.utc),
                )
                
                updated_package = await service.confirm_submission(confirm_request)
                
                assert updated_package.mndes_submission_started is True
                assert updated_package.exhibits[0].mndes_submitted_by_user is True
                assert updated_package.exhibits[0].mndes_tracking_number == "MN123456789"
    
    @pytest.mark.asyncio
    async def test_confirm_submission_all_exhibits(self, service, create_request, sample_vault_docs):
        """Test that submission_complete is set when all exhibits are submitted."""
        with patch.object(service, '_save_package_to_db', new_callable=AsyncMock):
            package = await service.create_package(
                request=create_request,
                vault_docs=sample_vault_docs,
                user_id="user_123",
            )
            
            # Confirm all exhibits one by one
            for i, exhibit in enumerate(package.exhibits):
                with patch.object(service, 'get_package', new_callable=AsyncMock, return_value=package):
                    confirm_request = MNDESSubmissionConfirmRequest(
                        package_id=package.package_id,
                        exhibit_id=exhibit.exhibit_id,
                        mndes_tracking_number=f"MN{i+1:09d}",
                    )
                    package = await service.confirm_submission(confirm_request)
            
            assert package.mndes_submission_complete is True


class TestComplianceSummary:
    """Test compliance summary functionality."""

    @pytest.mark.asyncio
    async def test_get_compliance_summary(self, service, create_request, sample_vault_docs):
        """Test compliance summary generation."""
        with patch.object(service, '_save_package_to_db', new_callable=AsyncMock):
            package = await service.create_package(
                request=create_request,
                vault_docs=sample_vault_docs,
                user_id="user_123",
            )
            
            with patch.object(service, 'get_package', new_callable=AsyncMock, return_value=package):
                summary = await service.get_compliance_summary(package.package_id)
                
                assert summary.total_files == 3
                assert summary.all_clear is not None  # Could be True or False depending on validation
                assert summary.compliant >= 0
                assert summary.non_compliant >= 0
    
    @pytest.mark.asyncio
    async def test_get_compliance_summary_not_found(self, service):
        """Test compliance summary for non-existent package."""
        with patch.object(service, 'get_package', new_callable=AsyncMock, return_value=None):
            with pytest.raises(ValueError, match="Package not_found not found"):
                await service.get_compliance_summary("not_found")


class TestSubmissionChecklist:
    """Test submission checklist functionality."""

    @pytest.mark.asyncio
    async def test_get_submission_checklist(self, service, create_request, sample_vault_docs):
        """Test submission checklist generation."""
        with patch.object(service, '_save_package_to_db', new_callable=AsyncMock):
            package = await service.create_package(
                request=create_request,
                vault_docs=sample_vault_docs,
                user_id="user_123",
            )
            
            with patch.object(service, 'get_package', new_callable=AsyncMock, return_value=package):
                checklist = await service.get_submission_checklist(package.package_id)
                
                assert checklist["package_id"] == package.package_id
                assert checklist["mn_case_number"] == package.mn_case_number
                assert "steps" in checklist
                assert len(checklist["steps"]) == 8  # 8-step checklist
                assert "warnings" in checklist
                assert "mndes_portal_url" in checklist
    
    @pytest.mark.asyncio
    async def test_get_submission_checklist_not_found(self, service):
        """Test checklist for non-existent package."""
        with patch.object(service, 'get_package', new_callable=AsyncMock, return_value=None):
            with pytest.raises(ValueError, match="Package not_found not found"):
                await service.get_submission_checklist("not_found")


class TestDatabasePersistence:
    """Test database persistence functionality."""

    @pytest.mark.asyncio
    async def test_package_to_db_model_conversion(self, service, create_request, sample_vault_docs):
        """Test conversion from Pydantic model to DB model."""
        with patch.object(service, '_save_package_to_db', new_callable=AsyncMock):
            package = await service.create_package(
                request=create_request,
                vault_docs=sample_vault_docs,
                user_id="user_123",
            )
            
            db_model = service._package_to_db_model(package)
            
            assert isinstance(db_model, MNDESExhibitPackageDB)
            assert db_model.package_id == package.package_id
            assert db_model.user_id == package.user_id
            assert db_model.mn_case_number == package.mn_case_number
            assert db_model.exhibits_json is not None
    
    @pytest.mark.asyncio
    async def test_package_from_db_model_conversion(self, service, create_request, sample_vault_docs):
        """Test conversion from DB model to Pydantic model."""
        with patch.object(service, '_save_package_to_db', new_callable=AsyncMock):
            package = await service.create_package(
                request=create_request,
                vault_docs=sample_vault_docs,
                user_id="user_123",
            )
            
            db_model = service._package_to_db_model(package)
            reconstructed = service._package_from_db_model(db_model)
            
            assert reconstructed.package_id == package.package_id
            assert reconstructed.user_id == package.user_id
            assert len(reconstructed.exhibits) == len(package.exhibits)


class TestDefaultExhibitName:
    """Test exhibit name generation."""

    def test_default_exhibit_name_simple(self, service):
        """Test default name generation from simple filename."""
        name = service._default_exhibit_name("lease_agreement.pdf")
        assert name == "lease agreement"
    
    def test_default_exhibit_name_with_dashes(self, service):
        """Test default name generation with dashes."""
        name = service._default_exhibit_name("notice-to-vacate.pdf")
        assert name == "notice to vacate"
    
    def test_default_exhibit_name_long(self, service):
        """Test that long names are truncated."""
        long_name = "a" * 100 + ".pdf"
        name = service._default_exhibit_name(long_name)
        assert len(name) <= 80
    
    def test_default_exhibit_name_no_extension(self, service):
        """Test default name generation without extension."""
        name = service._default_exhibit_name("document")
        assert name == "document"


# ============================================================================
# Integration Tests (requires database)
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestMNDESIntegration:
    """Integration tests with actual database."""
    
    async def test_full_package_lifecycle(self, service, create_request, sample_vault_docs):
        """Test complete package lifecycle with real DB."""
        # This test requires a real database connection
        # Skip if no DB available
        try:
            from app.core.database import get_db_session
            async with get_db_session() as session:
                pass  # Just test connection
        except Exception:
            pytest.skip("Database not available for integration tests")
        
        # Create package
        package = await service.create_package(
            request=create_request,
            vault_docs=sample_vault_docs,
            user_id="user_123",
        )
        
        # Verify saved to DB
        retrieved = await service.get_package(package.package_id)
        assert retrieved is not None
        assert retrieved.mn_case_number == package.mn_case_number
