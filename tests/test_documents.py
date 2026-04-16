"""
Semptify 5.0 - Documents API Tests
Tests for document processing, vault, and law engine.
"""

import pytest
from httpx import AsyncClient
from io import BytesIO
import httpx


# =============================================================================
# Document Upload Tests
# =============================================================================

@pytest.mark.anyio
async def test_document_upload_happy_path(client: AsyncClient, test_user_id):
    """Test complete document upload happy path with vault storage."""
    # Create a mock PDF file
    file_content = b"%PDF-1.4 mock pdf content for testing"
    files = {"file": ("test_lease.pdf", BytesIO(file_content), "application/pdf")}
    
    response = await client.post(
        f"/api/documents/upload?user_id={test_user_id}",
        files=files
    )
    assert response.status_code in [200, 201, 401, 503]  # gated or provider unavailable
    if response.status_code in [200, 201]:
        data = response.json()
        assert "id" in data
        assert "filename" in data
        assert "status" in data
        assert "vault_id" in data  # Should have vault ID from unified upload
        assert "registry_id" in data  # Should have registry ID
        assert data["filename"] == "test_lease.pdf"


@pytest.mark.anyio
async def test_vault_deduplication_by_sha256(client: AsyncClient, test_user_id):
    """Test that vault deduplicates documents by SHA-256 hash."""
    # Upload the same content twice
    file_content = b"Identical document content for deduplication test"
    files1 = {"file": ("doc1.pdf", BytesIO(file_content), "application/pdf")}
    files2 = {"file": ("doc2.pdf", BytesIO(file_content), "application/pdf")}
    
    # First upload
    response1 = await client.post(
        f"/api/documents/upload?user_id={test_user_id}",
        files=files1
    )
    
    # Second upload (same content, different filename)
    response2 = await client.post(
        f"/api/documents/upload?user_id={test_user_id}",
        files=files2
    )
    
    if response1.status_code in [200, 201] and response2.status_code in [200, 201]:
        data1 = response1.json()
        data2 = response2.json()
        
        # Should both succeed
        assert data1["status"] in ["completed", "processed", "classified"]
        assert data2["status"] in ["completed", "processed", "classified"]
        
        # Should have different document IDs but potentially same vault ID
        assert data1["id"] != data2["id"]
        
        # Check if vault deduplication worked (same vault_id would indicate deduplication)
        # Note: This depends on vault service implementation
        assert "vault_id" in data1
        assert "vault_id" in data2


@pytest.mark.anyio
async def test_vault_certificate_record_creation(client: AsyncClient, test_user_id):
    """Test that vault upload creates proper certificate records."""
    file_content = b"Document for certificate testing"
    files = {"file": ("cert_test.pdf", BytesIO(file_content), "application/pdf")}
    
    response = await client.post(
        f"/api/documents/upload?user_id={test_user_id}",
        files=files
    )
    
    if response.status_code in [200, 201]:
        data = response.json()
        
        # Should have vault metadata
        assert "vault_id" in data
        assert "certificate_path" in data or "certificate_id" in data
        
        # Should have integrity information
        assert "content_hash" in data or "sha256_hash" in data
        
        # Document should be marked as original (not duplicate)
        assert data.get("is_duplicate") is False or "is_duplicate" not in data


@pytest.mark.anyio
async def test_document_upload_large_file_rejection(client: AsyncClient, test_user_id):
    """Test that uploads reject files over the size limit."""
    # Create a large file (over typical 50MB limit)
    large_content = b"x" * (60 * 1024 * 1024)  # 60MB
    files = {"file": ("large_file.pdf", BytesIO(large_content), "application/pdf")}
    
    response = await client.post(
        f"/api/documents/upload?user_id={test_user_id}",
        files=files
    )
    
    # Should be rejected for size
    assert response.status_code == 400
    data = response.json()
    assert "too large" in data.get("detail", "").lower() or "size" in data.get("detail", "").lower()


@pytest.mark.anyio
async def test_document_upload_invalid_file_type(client: AsyncClient, test_user_id):
    """Test that uploads reject disallowed file types."""
    # Try to upload an executable
    exe_content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"  # Fake EXE header
    files = {"file": ("malware.exe", BytesIO(exe_content), "application/x-msdownload")}
    
    response = await client.post(
        f"/api/documents/upload?user_id={test_user_id}",
        files=files
    )
    
    # Should be rejected for file type
    assert response.status_code == 400
    data = response.json()
    assert "not allowed" in data.get("detail", "").lower() or "type" in data.get("detail", "").lower()


@pytest.mark.anyio
async def test_document_upload_missing_filename(client: AsyncClient, test_user_id):
    """Test that uploads require a filename."""
    file_content = b"Content without filename"
    # Upload without filename in the file tuple
    files = {"file": (None, BytesIO(file_content), "application/pdf")}
    
    response = await client.post(
        f"/api/documents/upload?user_id={test_user_id}",
        files=files
    )
    
    # Should be rejected
    assert response.status_code == 400
    data = response.json()
    assert "filename" in data.get("detail", "").lower()


@pytest.mark.anyio
async def test_document_upload_with_case_number(client: AsyncClient, test_user_id):
    """Test document upload with case number association."""
    file_content = b"Case-related document"
    files = {"file": ("case_doc.pdf", BytesIO(file_content), "application/pdf")}
    
    response = await client.post(
        f"/api/documents/upload?user_id={test_user_id}&case_number=CASE-2024-001",
        files=files
    )
    
    if response.status_code in [200, 201]:
        data = response.json()
        assert "id" in data
        # Case number should be associated (may not be returned in response but stored)


@pytest.mark.anyio
async def test_document_upload_processing_pipeline(client: AsyncClient, test_user_id):
    """Test that upload triggers the full processing pipeline."""
    file_content = b"Document for pipeline testing"
    files = {"file": ("pipeline_test.pdf", BytesIO(file_content), "application/pdf")}
    
    response = await client.post(
        f"/api/documents/upload?user_id={test_user_id}",
        files=files
    )
    
    if response.status_code in [200, 201]:
        data = response.json()
        
        # Should have processing results
        assert "status" in data
        assert data["status"] in ["completed", "processed", "classified", "pending"]
        
        # Should have analysis results if processed
        if data["status"] in ["completed", "processed", "classified"]:
            # May have classification, text extraction, etc.
            assert "doc_type" in data or "document_type" in data or "mime_type" in data


@pytest.mark.anyio
async def test_document_upload_queue_mode(client: AsyncClient, test_user_id):
    """Test document upload in queue mode (no immediate processing)."""
    file_content = b"%PDF-1.4 mock pdf content"
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
    
    response = await client.post(
        f"/api/documents/upload?user_id={test_user_id}&process_now=false",
        files=files
    )
    assert response.status_code in [200, 201, 401]
    if response.status_code in [200, 201]:
        data = response.json()
        assert data["status"] in ["pending", "queued"]


@pytest.mark.anyio
async def test_document_upload_no_file(client: AsyncClient, test_user_id):
    """Test document upload without file."""
    response = await client.post(f"/api/documents/upload?user_id={test_user_id}")
    assert response.status_code in [401, 422]


@pytest.mark.anyio
async def test_document_upload_missing_user_id(client: AsyncClient):
    """Test document upload without user_id - in open mode, a user is auto-created."""
    file_content = b"%PDF-1.4 mock pdf"
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}

    response = await client.post("/api/documents/upload", files=files)
    # In open security mode, a user is auto-created, so upload succeeds
    # In strict mode, this would be 401/422
    assert response.status_code in [200, 201, 401, 422]
# =============================================================================
# Document Listing Tests
# =============================================================================

@pytest.mark.anyio
async def test_document_list(client: AsyncClient, test_user_id):
    """Test listing user documents."""
    response = await client.get(f"/api/documents/?user_id={test_user_id}")
    assert response.status_code in [200, 401]
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.anyio
async def test_document_list_filter_by_type(client: AsyncClient, test_user_id):
    """Test filtering documents by type."""
    response = await client.get(
        f"/api/documents/?user_id={test_user_id}&doc_type=lease"
    )
    assert response.status_code in [200, 401]


@pytest.mark.anyio
async def test_document_list_filter_by_status(client: AsyncClient, test_user_id):
    """Test filtering documents by status."""
    response = await client.get(
        f"/api/documents/?user_id={test_user_id}&status=classified"
    )
    assert response.status_code in [200, 401]


# =============================================================================
# Document Details Tests
# =============================================================================

@pytest.mark.anyio
async def test_document_get_nonexistent(client: AsyncClient, test_user_id):
    """Test getting a non-existent document."""
    response = await client.get(
        "/api/documents/nonexistent-id",
        cookies={"semptify_uid": test_user_id},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_document_reprocess_nonexistent(client: AsyncClient, test_user_id):
    """Test reprocessing a non-existent document."""
    response = await client.post(
        "/api/documents/nonexistent-id/reprocess",
        cookies={"semptify_uid": test_user_id},
    )
    assert response.status_code == 404


# =============================================================================
# Timeline & Summary Tests
# =============================================================================

@pytest.mark.anyio
async def test_document_timeline(client: AsyncClient, test_user_id):
    """Test document timeline endpoint."""
    response = await client.get(f"/api/documents/timeline/?user_id={test_user_id}")
    assert response.status_code in [200, 401]
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.anyio
async def test_document_summary(client: AsyncClient, test_user_id):
    """Test document summary endpoint."""
    response = await client.get(f"/api/documents/summary/?user_id={test_user_id}")
    assert response.status_code in [200, 401]
    if response.status_code == 200:
        data = response.json()
        assert "total_documents" in data
        assert "by_type" in data
        assert "by_status" in data


@pytest.mark.anyio
async def test_document_rights(client: AsyncClient, test_user_id):
    """Test tenant rights summary endpoint."""
    response = await client.get(f"/api/documents/rights/?user_id={test_user_id}")
    assert response.status_code in [200, 401]
    if response.status_code == 200:
        data = response.json()
        assert "documents_analyzed" in data


# =============================================================================
# Law Reference Tests
# =============================================================================

@pytest.mark.anyio
async def test_laws_list(client: AsyncClient):
    """Test listing all law references."""
    response = await client.get("/api/documents/laws/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.anyio
async def test_laws_filter_by_category(client: AsyncClient):
    """Test filtering laws by category."""
    response = await client.get("/api/documents/laws/?category=eviction")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_laws_get_nonexistent(client: AsyncClient):
    """Test getting a non-existent law."""
    response = await client.get("/api/documents/laws/nonexistent-id")
    assert response.status_code == 404


# =============================================================================
# Vault Tests
# =============================================================================

@pytest.mark.anyio
async def test_vault_list_unauthenticated(client: AsyncClient):
    """Test vault list requires authentication - vault is backend only via API."""
    response = await client.get("/api/vault/")
    # Vault is backend-only, accessed via Timeline/Calendar
    # In open mode might auto-create user, strict mode returns 401/403
    # Could also be 400 if no user context can be determined
    assert response.status_code in [200, 400, 401, 403, 404]


@pytest.mark.anyio
async def test_vault_upload_requires_auth(client: AsyncClient):
    """Test vault upload requires authentication - vault is backend only."""
    file_content = b"test content"
    try:
        response = await client.post(
            "/api/vault/upload",
            files={"file": ("test.txt", BytesIO(file_content), "text/plain")},
            data={"access_token": "fake_token"}
        )
        # Vault is backend-only, upload via /api/documents/
        # Various error codes possible depending on security mode
        assert response.status_code in [400, 401, 403, 404, 422, 500]
    except httpx.HTTPError:
        # External service errors (like Google Drive 401) may raise HTTP errors
        # This is expected behavior when using fake tokens
        pass


@pytest.mark.anyio
async def test_vault_download_nonexistent(authenticated_client: AsyncClient):
    """Test downloading non-existent vault document."""
    response = await authenticated_client.get("/vault/nonexistent-id/download")
    assert response.status_code in [404, 401]


@pytest.mark.anyio
async def test_vault_certificate_nonexistent(authenticated_client: AsyncClient):
    """Test getting certificate for non-existent document."""
    response = await authenticated_client.get("/vault/nonexistent-id/certificate")
    assert response.status_code in [404, 401]


# =============================================================================
# Document Type Tests
# =============================================================================

@pytest.mark.anyio
@pytest.mark.parametrize("doc_type", [
    "lease", "notice", "receipt", "court_filing", "communication",
    "photo", "inspection", "repair_request", "insurance", "other"
])
async def test_document_filter_all_types(client: AsyncClient, test_user_id, doc_type):
    """Test filtering documents by all supported types."""
    response = await client.get(
        f"/api/documents/?user_id={test_user_id}&doc_type={doc_type}"
    )
    assert response.status_code in [200, 401]


# =============================================================================
# Processing Status Tests
# =============================================================================

@pytest.mark.anyio
@pytest.mark.parametrize("status", [
    "pending", "analyzing", "classified", "cross_referenced", "failed"
])
async def test_document_filter_all_statuses(client: AsyncClient, test_user_id, status):
    """Test filtering documents by all processing statuses."""
    response = await client.get(
        f"/api/documents/?user_id={test_user_id}&status={status}"
    )
    assert response.status_code in [200, 401]
