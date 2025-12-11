"""
Semptify 5.0 - Briefcase Tests
Tests for document organization, folder management, and batch operations.
"""

import pytest
from httpx import AsyncClient, ASGITransport
import io
import json

# Test environment setup
import os
os.environ["SECURITY_MODE"] = "open"
os.environ["TESTING"] = "true"

from app.main import app


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_pdf_content():
    """Create sample PDF-like content for testing."""
    return b"%PDF-1.4 test content"


@pytest.fixture
def sample_text_content():
    """Create sample text content for testing."""
    return b"This is a test document with some text content."


# =============================================================================
# Briefcase Root Tests
# =============================================================================

class TestBriefcaseRoot:
    """Test the main briefcase endpoint."""

    @pytest.mark.anyio
    async def test_get_briefcase(self, client):
        """Test getting the entire briefcase structure."""
        response = await client.get("/api/briefcase/")
        assert response.status_code == 200
        
        data = response.json()
        assert "folders" in data
        assert "documents" in data
        assert "tags" in data
        assert "stats" in data
        
        # Should have default folders
        folder_ids = [f["id"] for f in data["folders"]]
        assert "root" in folder_ids
        assert "extracted" in folder_ids
        assert "highlights" in folder_ids
        assert "evidence" in folder_ids

    @pytest.mark.anyio
    async def test_briefcase_stats(self, client):
        """Test briefcase statistics."""
        response = await client.get("/api/briefcase/stats")
        assert response.status_code == 200
        
        stats = response.json()
        assert "total_folders" in stats
        assert "total_documents" in stats
        assert "total_size" in stats
        assert stats["total_folders"] >= 4  # Default folders


# =============================================================================
# Folder Tests
# =============================================================================

class TestFolders:
    """Test folder operations."""

    @pytest.mark.anyio
    async def test_create_folder(self, client):
        """Test creating a new folder."""
        response = await client.post(
            "/api/briefcase/folder",
            json={
                "name": "Test Folder",
                "parent_id": "root",
                "color": "#ff5733"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["folder"]["name"] == "Test Folder"
        assert data["folder"]["color"] == "#ff5733"
        assert data["folder"]["parent_id"] == "root"

    @pytest.mark.anyio
    async def test_get_folder_contents(self, client):
        """Test getting folder contents."""
        response = await client.get("/api/briefcase/folder/root")
        assert response.status_code == 200
        
        data = response.json()
        assert "folder" in data
        assert "subfolders" in data
        assert "documents" in data
        assert "breadcrumb" in data
        
        # Root should have default subfolders
        assert len(data["subfolders"]) >= 3

    @pytest.mark.anyio
    async def test_get_nonexistent_folder(self, client):
        """Test getting a folder that doesn't exist."""
        response = await client.get("/api/briefcase/folder/nonexistent")
        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_update_folder(self, client):
        """Test updating a folder."""
        # First create a folder
        create_response = await client.post(
            "/api/briefcase/folder",
            json={"name": "Original Name", "parent_id": "root"}
        )
        folder_id = create_response.json()["folder"]["id"]
        
        # Update it
        response = await client.put(
            f"/api/briefcase/folder/{folder_id}",
            json={"name": "Updated Name", "color": "#00ff00"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["folder"]["name"] == "Updated Name"
        assert data["folder"]["color"] == "#00ff00"

    @pytest.mark.anyio
    async def test_cannot_modify_root(self, client):
        """Test that root folder cannot be modified."""
        response = await client.put(
            "/api/briefcase/folder/root",
            json={"name": "New Root Name"}
        )
        assert response.status_code == 400

    @pytest.mark.anyio
    async def test_delete_empty_folder(self, client):
        """Test deleting an empty folder."""
        # Create folder
        create_response = await client.post(
            "/api/briefcase/folder",
            json={"name": "To Delete", "parent_id": "root"}
        )
        folder_id = create_response.json()["folder"]["id"]
        
        # Delete it
        response = await client.delete(f"/api/briefcase/folder/{folder_id}")
        assert response.status_code == 200
        
        # Verify it's gone
        get_response = await client.get(f"/api/briefcase/folder/{folder_id}")
        assert get_response.status_code == 404


# =============================================================================
# Document Tests
# =============================================================================

class TestDocuments:
    """Test document operations."""

    @pytest.mark.anyio
    async def test_upload_document(self, client, sample_text_content):
        """Test uploading a document."""
        files = {"file": ("test.txt", io.BytesIO(sample_text_content), "text/plain")}
        data = {"folder_id": "root", "tags": "test,important", "notes": "Test notes"}
        
        response = await client.post(
            "/api/briefcase/document",
            files=files,
            data=data
        )
        assert response.status_code == 200
        
        result = response.json()
        assert result["success"] is True
        assert result["document"]["name"] == "test.txt"
        assert "test" in result["document"]["tags"]
        assert result["document"]["notes"] == "Test notes"

    @pytest.mark.anyio
    async def test_get_document(self, client, sample_text_content):
        """Test getting document metadata."""
        # Upload first
        files = {"file": ("test.txt", io.BytesIO(sample_text_content), "text/plain")}
        upload_response = await client.post(
            "/api/briefcase/document",
            files=files,
            data={"folder_id": "root"}
        )
        doc_id = upload_response.json()["document"]["id"]
        
        # Get metadata
        response = await client.get(f"/api/briefcase/document/{doc_id}")
        assert response.status_code == 200
        
        doc = response.json()
        assert doc["name"] == "test.txt"
        assert "content" not in doc  # Content should not be in metadata

    @pytest.mark.anyio
    async def test_download_document(self, client, sample_text_content):
        """Test downloading a document."""
        # Upload first
        files = {"file": ("test.txt", io.BytesIO(sample_text_content), "text/plain")}
        upload_response = await client.post(
            "/api/briefcase/document",
            files=files,
            data={"folder_id": "root"}
        )
        doc_id = upload_response.json()["document"]["id"]
        
        # Download
        response = await client.get(f"/api/briefcase/document/{doc_id}/download")
        assert response.status_code == 200
        assert response.content == sample_text_content

    @pytest.mark.anyio
    async def test_preview_document(self, client, sample_text_content):
        """Test document preview."""
        # Upload first
        files = {"file": ("test.txt", io.BytesIO(sample_text_content), "text/plain")}
        upload_response = await client.post(
            "/api/briefcase/document",
            files=files,
            data={"folder_id": "root"}
        )
        doc_id = upload_response.json()["document"]["id"]
        
        # Preview
        response = await client.get(f"/api/briefcase/document/{doc_id}/preview")
        assert response.status_code == 200
        
        data = response.json()
        assert "content" in data
        assert data["content"].startswith("data:")

    @pytest.mark.anyio
    async def test_update_document(self, client, sample_text_content):
        """Test updating document properties."""
        # Upload first
        files = {"file": ("test.txt", io.BytesIO(sample_text_content), "text/plain")}
        upload_response = await client.post(
            "/api/briefcase/document",
            files=files,
            data={"folder_id": "root"}
        )
        doc_id = upload_response.json()["document"]["id"]
        
        # Update
        response = await client.put(
            f"/api/briefcase/document/{doc_id}",
            json={"name": "renamed.txt", "starred": True, "tags": ["important"]}
        )
        assert response.status_code == 200
        
        doc = response.json()["document"]
        assert doc["name"] == "renamed.txt"
        assert doc["starred"] is True
        assert "important" in doc["tags"]

    @pytest.mark.anyio
    async def test_star_document(self, client, sample_text_content):
        """Test starring a document."""
        # Upload first
        files = {"file": ("test.txt", io.BytesIO(sample_text_content), "text/plain")}
        upload_response = await client.post(
            "/api/briefcase/document",
            files=files,
            data={"folder_id": "root"}
        )
        doc_id = upload_response.json()["document"]["id"]
        
        # Star it
        response = await client.put(
            f"/api/briefcase/document/{doc_id}",
            json={"starred": True}
        )
        assert response.status_code == 200
        
        # Check starred list
        starred_response = await client.get("/api/briefcase/starred")
        assert starred_response.status_code == 200
        
        starred = starred_response.json()
        assert starred["count"] >= 1

    @pytest.mark.anyio
    async def test_delete_document(self, client, sample_text_content):
        """Test deleting a document."""
        # Upload first
        files = {"file": ("test.txt", io.BytesIO(sample_text_content), "text/plain")}
        upload_response = await client.post(
            "/api/briefcase/document",
            files=files,
            data={"folder_id": "root"}
        )
        doc_id = upload_response.json()["document"]["id"]
        
        # Delete
        response = await client.delete(f"/api/briefcase/document/{doc_id}")
        assert response.status_code == 200
        
        # Verify it's gone
        get_response = await client.get(f"/api/briefcase/document/{doc_id}")
        assert get_response.status_code == 404


# =============================================================================
# Move/Copy Tests
# =============================================================================

class TestMoveCopy:
    """Test document move and copy operations."""

    @pytest.mark.anyio
    async def test_move_document(self, client, sample_text_content):
        """Test moving a document to another folder."""
        # Create a target folder
        folder_response = await client.post(
            "/api/briefcase/folder",
            json={"name": "Target Folder", "parent_id": "root"}
        )
        target_folder_id = folder_response.json()["folder"]["id"]
        
        # Upload a document to root
        files = {"file": ("test.txt", io.BytesIO(sample_text_content), "text/plain")}
        upload_response = await client.post(
            "/api/briefcase/document",
            files=files,
            data={"folder_id": "root"}
        )
        doc_id = upload_response.json()["document"]["id"]
        
        # Move it
        response = await client.post(
            f"/api/briefcase/document/{doc_id}/move",
            data={"folder_id": target_folder_id}
        )
        assert response.status_code == 200
        
        # Verify it moved
        doc_response = await client.get(f"/api/briefcase/document/{doc_id}")
        assert doc_response.json()["folder_id"] == target_folder_id

    @pytest.mark.anyio
    async def test_copy_document(self, client, sample_text_content):
        """Test copying a document to another folder."""
        # Create a target folder
        folder_response = await client.post(
            "/api/briefcase/folder",
            json={"name": "Copy Target", "parent_id": "root"}
        )
        target_folder_id = folder_response.json()["folder"]["id"]
        
        # Upload a document to root
        files = {"file": ("original.txt", io.BytesIO(sample_text_content), "text/plain")}
        upload_response = await client.post(
            "/api/briefcase/document",
            files=files,
            data={"folder_id": "root"}
        )
        original_doc_id = upload_response.json()["document"]["id"]
        
        # Copy it
        response = await client.post(
            f"/api/briefcase/document/{original_doc_id}/copy",
            data={"folder_id": target_folder_id}
        )
        assert response.status_code == 200
        
        copy = response.json()["document"]
        assert copy["folder_id"] == target_folder_id
        assert copy["name"].startswith("Copy of")
        assert copy["id"] != original_doc_id
        
        # Original should still be in root
        original_response = await client.get(f"/api/briefcase/document/{original_doc_id}")
        assert original_response.json()["folder_id"] == "root"


# =============================================================================
# Search Tests
# =============================================================================

class TestSearch:
    """Test document search functionality."""

    @pytest.mark.anyio
    async def test_search_by_name(self, client, sample_text_content):
        """Test searching documents by name."""
        # Upload a document with unique name
        files = {"file": ("unique_searchable_document.txt", io.BytesIO(sample_text_content), "text/plain")}
        await client.post(
            "/api/briefcase/document",
            files=files,
            data={"folder_id": "root"}
        )
        
        # Search for it
        response = await client.get("/api/briefcase/search?q=unique_searchable")
        assert response.status_code == 200
        
        results = response.json()
        assert results["count"] >= 1
        assert any("unique_searchable" in r["name"] for r in results["results"])

    @pytest.mark.anyio
    async def test_search_by_tag(self, client, sample_text_content):
        """Test searching documents by tag."""
        # Upload a document with specific tag
        files = {"file": ("tagged.txt", io.BytesIO(sample_text_content), "text/plain")}
        await client.post(
            "/api/briefcase/document",
            files=files,
            data={"folder_id": "root", "tags": "special_tag"}
        )
        
        # Search by tag
        response = await client.get("/api/briefcase/search?q=&tags=special_tag")
        assert response.status_code == 200
        
        results = response.json()
        assert results["count"] >= 1

    @pytest.mark.anyio
    async def test_search_starred(self, client, sample_text_content):
        """Test filtering starred documents."""
        # Upload and star a document
        files = {"file": ("starred.txt", io.BytesIO(sample_text_content), "text/plain")}
        upload_response = await client.post(
            "/api/briefcase/document",
            files=files,
            data={"folder_id": "root"}
        )
        doc_id = upload_response.json()["document"]["id"]
        
        await client.put(
            f"/api/briefcase/document/{doc_id}",
            json={"starred": True}
        )
        
        # Search starred
        response = await client.get("/api/briefcase/search?q=&starred=true")
        assert response.status_code == 200
        
        results = response.json()
        assert all(r["starred"] for r in results["results"])


# =============================================================================
# Tags Tests
# =============================================================================

class TestTags:
    """Test tag management."""

    @pytest.mark.anyio
    async def test_get_all_tags(self, client):
        """Test getting all available tags."""
        response = await client.get("/api/briefcase/tags")
        assert response.status_code == 200
        
        data = response.json()
        assert "tags" in data
        # Should have default tags
        assert len(data["tags"]) > 0

    @pytest.mark.anyio
    async def test_add_tag(self, client):
        """Test adding a new tag."""
        response = await client.post(
            "/api/briefcase/tags",
            data={"tag": "NewCustomTag"}
        )
        assert response.status_code == 200
        
        tags = response.json()["tags"]
        assert "NewCustomTag" in tags


# =============================================================================
# Recent Documents Tests
# =============================================================================

class TestRecent:
    """Test recent documents functionality."""

    @pytest.mark.anyio
    async def test_get_recent_documents(self, client, sample_text_content):
        """Test getting recently added documents."""
        # Upload a few documents
        for i in range(3):
            files = {"file": (f"recent_{i}.txt", io.BytesIO(sample_text_content), "text/plain")}
            await client.post(
                "/api/briefcase/document",
                files=files,
                data={"folder_id": "root"}
            )
        
        # Get recent
        response = await client.get("/api/briefcase/recent?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert "documents" in data
        assert len(data["documents"]) >= 3


# =============================================================================
# Export Tests
# =============================================================================

class TestExport:
    """Test export functionality."""

    @pytest.mark.anyio
    async def test_export_folder_as_zip(self, client, sample_text_content):
        """Test exporting a folder as ZIP."""
        # Upload a document
        files = {"file": ("export_test.txt", io.BytesIO(sample_text_content), "text/plain")}
        await client.post(
            "/api/briefcase/document",
            files=files,
            data={"folder_id": "root"}
        )
        
        # Export root folder
        response = await client.post(
            "/api/briefcase/export",
            data={"folder_id": "root"}
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/zip"


# =============================================================================
# Extractions Tests
# =============================================================================

class TestExtractions:
    """Test PDF page extractions storage."""

    @pytest.mark.anyio
    async def test_save_extraction(self, client):
        """Test saving extracted pages."""
        response = await client.post(
            "/api/briefcase/extraction",
            data={
                "pdf_name": "test_document.pdf",
                "pages": json.dumps([1, 2, 3]),
                "notes": "Important pages"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["extraction"]["pdf_name"] == "test_document.pdf"
        assert data["extraction"]["pages"] == [1, 2, 3]

    @pytest.mark.anyio
    async def test_list_extractions(self, client):
        """Test listing extractions."""
        # Save an extraction first
        await client.post(
            "/api/briefcase/extraction",
            data={
                "pdf_name": "test.pdf",
                "pages": json.dumps([1])
            }
        )
        
        response = await client.get("/api/briefcase/extractions")
        assert response.status_code == 200
        
        data = response.json()
        assert "extractions" in data
        assert len(data["extractions"]) >= 1

    @pytest.mark.anyio
    async def test_delete_extraction(self, client):
        """Test deleting an extraction."""
        # Save an extraction
        create_response = await client.post(
            "/api/briefcase/extraction",
            data={
                "pdf_name": "to_delete.pdf",
                "pages": json.dumps([1])
            }
        )
        extraction_id = create_response.json()["extraction_id"]
        
        # Delete it
        response = await client.delete(f"/api/briefcase/extraction/{extraction_id}")
        assert response.status_code == 200
        
        # Verify it's gone
        get_response = await client.get(f"/api/briefcase/extraction/{extraction_id}")
        assert get_response.status_code == 404


# =============================================================================
# Highlights Tests
# =============================================================================

class TestHighlights:
    """Test highlights/annotations storage."""

    @pytest.mark.anyio
    async def test_save_highlight(self, client):
        """Test saving a highlight."""
        response = await client.post(
            "/api/briefcase/highlight",
            data={
                "pdf_name": "test_document.pdf",
                "page_number": 5,
                "color": "#ffff00",
                "color_name": "Yellow",
                "text": "Important text",
                "note": "Review this section"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["highlight"]["color"] == "#ffff00"
        assert data["highlight"]["note"] == "Review this section"

    @pytest.mark.anyio
    async def test_list_highlights(self, client):
        """Test listing highlights."""
        # Save a highlight first
        await client.post(
            "/api/briefcase/highlight",
            data={
                "pdf_name": "test.pdf",
                "page_number": 1,
                "color": "#ff0000"
            }
        )
        
        response = await client.get("/api/briefcase/highlights")
        assert response.status_code == 200
        
        data = response.json()
        assert "highlights" in data
        assert len(data["highlights"]) >= 1

    @pytest.mark.anyio
    async def test_batch_highlights(self, client):
        """Test saving multiple highlights at once."""
        response = await client.post(
            "/api/briefcase/highlights/batch",
            json={
                "pdf_name": "multi_highlight.pdf",
                "highlights": [
                    {"page": 1, "color": "#ffff00", "text": "First highlight"},
                    {"page": 2, "color": "#ff0000", "text": "Second highlight"},
                    {"page": 3, "color": "#00ff00", "text": "Third highlight"}
                ]
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 3

    @pytest.mark.anyio
    async def test_highlights_by_color(self, client):
        """Test getting highlights grouped by color."""
        # Save highlights with different colors
        for color in ["#ffff00", "#ff0000", "#ffff00"]:
            await client.post(
                "/api/briefcase/highlight",
                data={
                    "pdf_name": "test.pdf",
                    "page_number": 1,
                    "color": color
                }
            )
        
        response = await client.get("/api/briefcase/highlights/by-color")
        assert response.status_code == 200
        
        data = response.json()
        assert "groups" in data
