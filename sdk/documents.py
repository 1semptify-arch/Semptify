"""
Semptify SDK - Document Client

Handles document upload, management, and analysis.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO

from .base import BaseClient


@dataclass
class Document:
    """Document information."""
    id: str
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    document_type: str | None = None
    description: str | None = None
    tags: list[str] = None
    uploaded_at: datetime | None = None
    sha256_hash: str | None = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class IntakeDocument:
    """Document intake information with extraction results."""
    id: str
    filename: str
    status: str
    document_type: str | None = None
    extracted_dates: list[dict] = None
    extracted_amounts: list[dict] = None
    extracted_parties: list[dict] = None
    detected_issues: list[dict] = None

    def __post_init__(self):
        if self.extracted_dates is None:
            self.extracted_dates = []
        if self.extracted_amounts is None:
            self.extracted_amounts = []
        if self.extracted_parties is None:
            self.extracted_parties = []
        if self.detected_issues is None:
            self.detected_issues = []


class DocumentClient(BaseClient):
    """Client for document operations."""

    def upload(
        self,
        file: str | Path | BinaryIO,
        filename: str | None = None,
        document_type: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> Document:
        """
        Upload a document.
        
        Args:
            file: File path, Path object, or file-like object
            filename: Override filename (optional)
            document_type: Document type classification
            description: Document description
            tags: List of tags
            
        Returns:
            Uploaded document information
        """
        # Handle file input
        if isinstance(file, (str, Path)):
            file_path = Path(file)
            filename = filename or file_path.name
            with open(file_path, "rb") as f:
                content = f.read()
        else:
            content = file.read()
            filename = filename or getattr(file, "name", "document")

        # Prepare form data
        files = {"file": (filename, content)}
        data = {"user_id": self.user_id or ""}

        if document_type:
            data["document_type"] = document_type
        if description:
            data["description"] = description
        if tags:
            data["tags"] = ",".join(tags)

        response = self.post("/api/documents/upload", files=files, data=data)
        return Document(
            id=response.get("id", ""),
            filename=response.get("filename", filename),
            original_filename=response.get("original_filename", filename),
            file_size=response.get("file_size", len(content)),
            mime_type=response.get("mime_type", "application/octet-stream"),
            document_type=response.get("document_type"),
            description=response.get("description"),
            tags=response.get("tags", "").split(",") if response.get("tags") else [],
        )

    def intake_upload(
        self,
        file: str | Path | BinaryIO,
        filename: str | None = None,
        auto_process: bool = True,
    ) -> IntakeDocument:
        """
        Upload a document through the intake engine for automatic processing.
        
        Args:
            file: File path, Path object, or file-like object
            filename: Override filename (optional)
            auto_process: Whether to automatically process the document
            
        Returns:
            Intake document with extraction results
        """
        # Handle file input
        if isinstance(file, (str, Path)):
            file_path = Path(file)
            filename = filename or file_path.name
            with open(file_path, "rb") as f:
                content = f.read()
        else:
            content = file.read()
            filename = filename or getattr(file, "name", "document")

        files = {"file": (filename, content)}
        data = {"user_id": self.user_id or ""}

        endpoint = "/api/intake/upload/auto" if auto_process else "/api/intake/upload"
        response = self.post(endpoint, files=files, data=data)

        return IntakeDocument(
            id=response.get("id", ""),
            filename=response.get("filename", filename),
            status=response.get("status", "received"),
            document_type=response.get("document_type"),
            extracted_dates=response.get("extracted_dates", []),
            extracted_amounts=response.get("extracted_amounts", []),
            extracted_parties=response.get("extracted_parties", []),
            detected_issues=response.get("detected_issues", []),
        )

    def get_document(self, doc_id: str) -> Document:
        """
        Get a document by ID.
        
        Args:
            doc_id: The document ID
            
        Returns:
            Document information
        """
        response = self.get(f"/api/documents/{doc_id}")
        return Document(
            id=response.get("id", doc_id),
            filename=response.get("filename", ""),
            original_filename=response.get("original_filename", ""),
            file_size=response.get("file_size", 0),
            mime_type=response.get("mime_type", ""),
            document_type=response.get("document_type"),
            description=response.get("description"),
            tags=response.get("tags", "").split(",") if response.get("tags") else [],
        )

    def list_documents(
        self,
        document_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Document]:
        """
        List documents.
        
        Args:
            document_type: Filter by document type
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            
        Returns:
            List of documents
        """
        params = {"limit": limit, "offset": offset}
        if document_type:
            params["document_type"] = document_type

        response = self.get("/api/documents", params=params)
        documents = response if isinstance(response, list) else response.get("documents", [])

        return [
            Document(
                id=doc.get("id", ""),
                filename=doc.get("filename", ""),
                original_filename=doc.get("original_filename", ""),
                file_size=doc.get("file_size", 0),
                mime_type=doc.get("mime_type", ""),
                document_type=doc.get("document_type"),
                description=doc.get("description"),
            )
            for doc in documents
        ]

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document.
        
        Args:
            doc_id: The document ID
            
        Returns:
            True if deleted successfully
        """
        self.delete(f"/api/documents/{doc_id}")
        return True

    def download(self, doc_id: str, output_path: str | Path | None = None) -> bytes:
        """
        Download a document.
        
        Args:
            doc_id: The document ID
            output_path: Optional path to save the file
            
        Returns:
            Document content as bytes
        """
        response = self.client.get(f"/api/documents/{doc_id}/download")
        content = response.content

        if output_path:
            with open(output_path, "wb") as f:
                f.write(content)

        return content

    def get_intake_status(self, doc_id: str) -> dict[str, Any]:
        """
        Get intake processing status for a document.
        
        Args:
            doc_id: The document ID
            
        Returns:
            Processing status information
        """
        return self.get(f"/api/intake/status/{doc_id}")

    def get_critical_issues(self) -> list[dict[str, Any]]:
        """
        Get all critical issues from processed documents.
        
        Returns:
            List of critical issues requiring attention
        """
        response = self.get("/api/intake/issues/critical")
        return response if isinstance(response, list) else response.get("issues", [])

    def get_upcoming_deadlines(self, days: int = 14) -> list[dict[str, Any]]:
        """
        Get upcoming deadlines from processed documents.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of upcoming deadlines
        """
        response = self.get("/api/intake/deadlines/upcoming", params={"days": days})
        return response if isinstance(response, list) else response.get("deadlines", [])
