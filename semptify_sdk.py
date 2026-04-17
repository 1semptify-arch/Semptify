#!/usr/bin/env python3
"""
Semptify SDK - Single File Implementation

A comprehensive Python client for the Semptify 5.0 API.
All functionality in a single file for easy integration.

Usage:
    from semptify_sdk import SemptifyClient
    
    client = SemptifyClient("http://localhost:8000")
    client.auth.login("google_drive")
    doc = client.documents.upload("lease.pdf")
    analysis = client.copilot.analyze_case()
"""

import httpx
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path


# =============================================================================
# EXCEPTIONS
# =============================================================================

class SemptifyError(Exception):
    """Base exception for all Semptify SDK errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response_data: Optional[Dict] = None, request_id: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        self.request_id = request_id

class AuthenticationError(SemptifyError):
    """Authentication failed."""
    pass

class NotFoundError(SemptifyError):
    """Resource not found."""
    pass

class ValidationError(SemptifyError):
    """Validation error."""
    pass

class RateLimitError(SemptifyError):
    """Rate limit exceeded."""
    def __init__(self, message: str, retry_after: int, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after

class ServerError(SemptifyError):
    """Server error."""
    pass

class StorageRequiredError(SemptifyError):
    """Storage connection required."""
    def __init__(self, message: str, redirect_url: str, **kwargs):
        super().__init__(message, **kwargs)
        self.redirect_url = redirect_url


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class UserInfo:
    """User information."""
    user_id: str
    provider: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str = "user"

@dataclass
class StorageProvider:
    """Storage provider information."""
    id: str
    name: str
    icon: str
    connected: bool = False

@dataclass
class Document:
    """Document information."""
    id: str
    filename: str
    document_type: str
    file_size: int
    content_type: str
    created_at: datetime
    updated_at: datetime
    storage_provider: str
    storage_path: str
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class TimelineEvent:
    """Timeline event."""
    id: str
    title: str
    description: str
    event_type: str
    event_date: datetime
    created_at: datetime
    is_evidence: bool = False
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class Complaint:
    """Complaint information."""
    id: str
    complaint_type: str
    title: str
    description: str
    status: str
    created_at: datetime
    target_agency: Optional[str] = None
    violations: Optional[List[str]] = None

@dataclass
class Briefcase:
    """Briefcase information."""
    id: str
    name: str
    description: Optional[str] = None
    case_type: Optional[str] = None
    status: str = "active"
    item_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class VaultItem:
    """Vault item information."""
    id: str
    name: str
    item_type: str
    access_type: str = "private"
    description: Optional[str] = None
    document_id: Optional[str] = None
    encrypted: bool = True
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


# =============================================================================
# BASE HTTP CLIENT
# =============================================================================

class BaseClient:
    """Base HTTP client with error handling and authentication."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
        user_id: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.user_id = user_id
        self._client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.Client:
        """Get or create sync HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                cookies=self._get_cookies(),
            )
        return self._client
    
    @client.setter
    def client(self, client: httpx.Client) -> None:
        """Set the sync HTTP client."""
        self._client = client
    
    @property
    def async_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                cookies=self._get_cookies(),
            )
        return self._async_client
    
    @async_client.setter
    def async_client(self, client: httpx.AsyncClient) -> None:
        """Set the async HTTP client."""
        self._async_client = client
    
    def _get_cookies(self) -> Dict[str, str]:
        """Get authentication cookies."""
        cookies = {}
        if self.user_id:
            cookies["semptify_uid"] = self.user_id
        return cookies
    
    def set_user_id(self, user_id: str) -> None:
        """Set the user ID for authentication."""
        self.user_id = user_id
        if self._client:
            self._client.close()
            self._client = None
        if self._async_client:
            self._async_client = None
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle HTTP response and raise appropriate exceptions."""
        request_id = response.headers.get("x-request-id")
        
        # Success responses
        if response.status_code < 400:
            if response.headers.get("content-type", "").startswith("application/json"):
                return response.json()
            return {"content": response.text, "status_code": response.status_code}
        
        # Parse error response
        try:
            data = response.json()
        except json.JSONDecodeError:
            data = {"message": response.text}
        
        # Extract error details
        error_msg = data.get("detail") or data.get("message") or data.get("error") or "Unknown error"
        
        # Handle specific error codes
        if response.status_code == 401:
            if data.get("error") == "storage_required":
                raise StorageRequiredError(
                    message=error_msg,
                    redirect_url=data.get("redirect_url", "/storage/providers"),
                    response_data=data,
                    request_id=request_id,
                )
            raise AuthenticationError(
                message=error_msg,
                status_code=401,
                response_data=data,
                request_id=request_id,
            )
        
        if response.status_code == 403:
            raise AuthenticationError(
                message=error_msg,
                status_code=403,
                response_data=data,
                request_id=request_id,
            )
        
        if response.status_code == 404:
            raise NotFoundError(
                resource_type="Resource",
                response_data=data,
                request_id=request_id,
            )
        
        if response.status_code == 422:
            raise ValidationError(
                message=error_msg,
                errors=data.get("detail", []),
                response_data=data,
                request_id=request_id,
            )
        
        if response.status_code == 429:
            raise RateLimitError(
                message=error_msg,
                retry_after=int(response.headers.get("retry-after", 60)),
                response_data=data,
                request_id=request_id,
            )
        
        if response.status_code >= 500:
            raise ServerError(
                message=error_msg,
                status_code=response.status_code,
                response_data=data,
                request_id=request_id,
            )
        
        raise SemptifyError(
            message=error_msg,
            status_code=response.status_code,
            response_data=data,
            request_id=request_id,
        )
    
    def get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GET request."""
        response = self.client.get(path, params=params)
        return self._handle_response(response)
    
    def post(
        self,
        path: str,
        json: Optional[Dict] = None,
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make a POST request."""
        response = self.client.post(path, json=json, data=data, files=files)
        return self._handle_response(response)
    
    def put(self, path: str, json: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a PUT request."""
        response = self.client.put(path, json=json)
        return self._handle_response(response)
    
    def patch(self, path: str, json: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a PATCH request."""
        response = self.client.patch(path, json=json)
        return self._handle_response(response)
    
    def delete(self, path: str) -> Dict[str, Any]:
        """Make a DELETE request."""
        response = self.client.delete(path)
        return self._handle_response(response)


# =============================================================================
# SERVICE CLIENTS
# =============================================================================

class AuthClient(BaseClient):
    """Authentication service client."""
    
    def get_providers(self) -> List[StorageProvider]:
        """Get available storage providers."""
        response = self.get("/storage/providers")
        if "content" in response:
            return [
                StorageProvider(id="google_drive", name="Google Drive", icon="google"),
                StorageProvider(id="dropbox", name="Dropbox", icon="dropbox"),
                StorageProvider(id="onedrive", name="OneDrive", icon="microsoft"),
            ]
        return [StorageProvider(**p) for p in response.get("providers", [])]
    
    def get_auth_url(self, provider: str) -> str:
        """Get OAuth authorization URL."""
        response = self.client.get(f"/storage/auth/{provider}", follow_redirects=False)
        if response.status_code in [302, 307]:
            return response.headers.get("location", "")
        return self._handle_response(response).get("auth_url", "")
    
    def complete_oauth(self, provider: str, code: str, state: str) -> UserInfo:
        """Complete OAuth flow with authorization code."""
        response = self.get(
            f"/storage/callback/{provider}",
            params={"code": code, "state": state}
        )
        self.set_user_id(response.get("user_id", ""))
        return UserInfo(
            user_id=response.get("user_id", ""),
            provider=provider,
            email=response.get("email"),
            display_name=response.get("display_name"),
        )
    
    def get_current_user(self) -> Optional[UserInfo]:
        """Get currently authenticated user."""
        try:
            response = self.get("/api/auth/me")
            return UserInfo(
                user_id=response.get("user_id", ""),
                provider=response.get("provider", ""),
                email=response.get("email"),
                display_name=response.get("display_name"),
                avatar_url=response.get("avatar_url"),
                role=response.get("role", "user"),
            )
        except Exception:
            return None
    
    def logout(self) -> bool:
        """Log out current user."""
        try:
            self.post("/api/auth/logout")
            self.user_id = None
            return True
        except Exception:
            return False
    
    def validate_session(self) -> bool:
        """Validate current session."""
        try:
            response = self.post("/api/auth/validate")
            return response.get("valid", False)
        except Exception:
            return False
    
    def switch_role(self, role: str) -> UserInfo:
        """Switch user role."""
        response = self.post("/api/auth/switch_role", json={"role": role})
        return UserInfo(
            user_id=response.get("user_id", ""),
            provider=response.get("provider", ""),
            email=response.get("email"),
            display_name=response.get("display_name"),
            role=response.get("role", role),
        )


class DocumentClient(BaseClient):
    """Document management service client."""
    
    def upload(self, file_path: str, document_type: str = "general") -> Document:
        """Upload a document."""
        with open(file_path, "rb") as f:
            files = {"file": (Path(file_path).name, f, "application/octet-stream")}
            data = {"document_type": document_type}
            response = self.post("/api/documents/upload", files=files, data=data)
        
        return Document(
            id=response.get("id", ""),
            filename=response.get("filename", ""),
            document_type=response.get("document_type", ""),
            file_size=response.get("file_size", 0),
            content_type=response.get("content_type", ""),
            created_at=datetime.fromisoformat(response.get("created_at", "")),
            updated_at=datetime.fromisoformat(response.get("updated_at", "")),
            storage_provider=response.get("storage_provider", ""),
            storage_path=response.get("storage_path", ""),
            metadata=response.get("metadata", {}),
        )
    
    def intake_upload(self, file_path: str) -> Document:
        """Upload document through intake engine."""
        with open(file_path, "rb") as f:
            files = {"file": (Path(file_path).name, f, "application/octet-stream")}
            response = self.post("/api/documents/intake_upload", files=files)
        
        return Document(
            id=response.get("id", ""),
            filename=response.get("filename", ""),
            document_type=response.get("document_type", ""),
            file_size=response.get("file_size", 0),
            content_type=response.get("content_type", ""),
            created_at=datetime.fromisoformat(response.get("created_at", "")),
            updated_at=datetime.fromisoformat(response.get("updated_at", "")),
            storage_provider=response.get("storage_provider", ""),
            storage_path=response.get("storage_path", ""),
            metadata=response.get("metadata", {}),
        )
    
    def get(self, document_id: str) -> Document:
        """Get document information."""
        response = self.get(f"/api/documents/{document_id}")
        return Document(
            id=response.get("id", ""),
            filename=response.get("filename", ""),
            document_type=response.get("document_type", ""),
            file_size=response.get("file_size", 0),
            content_type=response.get("content_type", ""),
            created_at=datetime.fromisoformat(response.get("created_at", "")),
            updated_at=datetime.fromisoformat(response.get("updated_at", "")),
            storage_provider=response.get("storage_provider", ""),
            storage_path=response.get("storage_path", ""),
            metadata=response.get("metadata", {}),
        )
    
    def list(self, limit: int = 50, offset: int = 0) -> List[Document]:
        """List documents."""
        response = self.get("/api/documents", params={"limit": limit, "offset": offset})
        documents = []
        for doc_data in response.get("documents", []):
            documents.append(Document(
                id=doc_data.get("id", ""),
                filename=doc_data.get("filename", ""),
                document_type=doc_data.get("document_type", ""),
                file_size=doc_data.get("file_size", 0),
                content_type=doc_data.get("content_type", ""),
                created_at=datetime.fromisoformat(doc_data.get("created_at", "")),
                updated_at=datetime.fromisoformat(doc_data.get("updated_at", "")),
                storage_provider=doc_data.get("storage_provider", ""),
                storage_path=doc_data.get("storage_path", ""),
                metadata=doc_data.get("metadata", {}),
            ))
        return documents
    
    def delete(self, document_id: str) -> bool:
        """Delete a document."""
        try:
            self.delete(f"/api/documents/{document_id}")
            return True
        except Exception:
            return False


class TimelineClient(BaseClient):
    """Timeline and deadline service client."""
    
    def create_event(self, title: str, description: str, event_type: str, 
                    event_date: datetime, is_evidence: bool = False) -> TimelineEvent:
        """Create a timeline event."""
        response = self.post("/api/timeline/events", json={
            "title": title,
            "description": description,
            "event_type": event_type,
            "event_date": event_date.isoformat(),
            "is_evidence": is_evidence,
        })
        
        return TimelineEvent(
            id=response.get("id", ""),
            title=response.get("title", ""),
            description=response.get("description", ""),
            event_type=response.get("event_type", ""),
            event_date=datetime.fromisoformat(response.get("event_date", "")),
            created_at=datetime.fromisoformat(response.get("created_at", "")),
            is_evidence=response.get("is_evidence", False),
            metadata=response.get("metadata", {}),
        )
    
    def get_events(self, limit: int = 50) -> List[TimelineEvent]:
        """Get timeline events."""
        response = self.get("/api/timeline/events", params={"limit": limit})
        events = []
        for event_data in response.get("events", []):
            events.append(TimelineEvent(
                id=event_data.get("id", ""),
                title=event_data.get("title", ""),
                description=event_data.get("description", ""),
                event_type=event_data.get("event_type", ""),
                event_date=datetime.fromisoformat(event_data.get("event_date", "")),
                created_at=datetime.fromisoformat(event_data.get("created_at", "")),
                is_evidence=event_data.get("is_evidence", False),
                metadata=event_data.get("metadata", {}),
            ))
        return events
    
    def get_deadlines(self, days_ahead: int = 30) -> List[TimelineEvent]:
        """Get upcoming deadlines."""
        response = self.get("/api/timeline/deadlines", params={"days_ahead": days_ahead})
        deadlines = []
        for deadline_data in response.get("deadlines", []):
            deadlines.append(TimelineEvent(
                id=deadline_data.get("id", ""),
                title=deadline_data.get("title", ""),
                description=deadline_data.get("description", ""),
                event_type=deadline_data.get("event_type", ""),
                event_date=datetime.fromisoformat(deadline_data.get("event_date", "")),
                created_at=datetime.fromisoformat(deadline_data.get("created_at", "")),
                is_evidence=deadline_data.get("is_evidence", False),
                metadata=deadline_data.get("metadata", {}),
            ))
        return deadlines


class CopilotClient(BaseClient):
    """AI copilot service client."""
    
    def analyze_case(self, document_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analyze case with AI."""
        data = {}
        if document_ids:
            data["document_ids"] = document_ids
        
        response = self.post("/api/copilot/analyze_case", json=data)
        return response
    
    def analyze_document(self, document_id: str) -> Dict[str, Any]:
        """Analyze a specific document."""
        response = self.post(f"/api/copilot/analyze_document/{document_id}")
        return response
    
    def get_recommendations(self, case_context: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get AI recommendations."""
        data = {}
        if case_context:
            data["case_context"] = case_context
        
        response = self.post("/api/copilot/recommendations", json=data)
        return response.get("recommendations", [])
    
    def chat(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Chat with AI copilot."""
        data = {"message": message}
        if context:
            data["context"] = context
        
        response = self.post("/api/copilot/chat", json=data)
        return response


class ComplaintClient(BaseClient):
    """Complaint management service client."""
    
    def create(self, complaint_type: str, title: str, description: str,
               target_agency: Optional[str] = None, violations: Optional[List[str]] = None) -> Complaint:
        """Create a complaint."""
        data = {
            "complaint_type": complaint_type,
            "title": title,
            "description": description,
        }
        if target_agency:
            data["target_agency"] = target_agency
        if violations:
            data["violations"] = violations
        
        response = self.post("/api/complaints", json=data)
        return Complaint(
            id=response.get("id", ""),
            complaint_type=response.get("complaint_type", ""),
            title=response.get("title", ""),
            description=response.get("description", ""),
            status=response.get("status", ""),
            created_at=datetime.fromisoformat(response.get("created_at", "")),
            target_agency=response.get("target_agency"),
            violations=response.get("violations", []),
        )
    
    def get(self, complaint_id: str) -> Complaint:
        """Get complaint information."""
        response = self.get(f"/api/complaints/{complaint_id}")
        return Complaint(
            id=response.get("id", ""),
            complaint_type=response.get("complaint_type", ""),
            title=response.get("title", ""),
            description=response.get("description", ""),
            status=response.get("status", ""),
            created_at=datetime.fromisoformat(response.get("created_at", "")),
            target_agency=response.get("target_agency"),
            violations=response.get("violations", []),
        )
    
    def list(self, status: Optional[str] = None) -> List[Complaint]:
        """List complaints."""
        params = {}
        if status:
            params["status"] = status
        
        response = self.get("/api/complaints", params=params)
        complaints = []
        for complaint_data in response.get("complaints", []):
            complaints.append(Complaint(
                id=complaint_data.get("id", ""),
                complaint_type=complaint_data.get("complaint_type", ""),
                title=complaint_data.get("title", ""),
                description=complaint_data.get("description", ""),
                status=complaint_data.get("status", ""),
                created_at=datetime.fromisoformat(complaint_data.get("created_at", "")),
                target_agency=complaint_data.get("target_agency"),
                violations=complaint_data.get("violations", []),
            ))
        return complaints


class BriefcaseClient(BaseClient):
    """Briefcase management service client."""
    
    def create(self, name: str, description: Optional[str] = None, 
               case_type: Optional[str] = None) -> Briefcase:
        """Create a briefcase."""
        data = {"name": name}
        if description:
            data["description"] = description
        if case_type:
            data["case_type"] = case_type
        
        response = self.post("/api/briefcases", json=data)
        return Briefcase(
            id=response.get("id", ""),
            name=response.get("name", ""),
            description=response.get("description"),
            case_type=response.get("case_type"),
            status=response.get("status", "active"),
            item_count=response.get("item_count", 0),
            created_at=datetime.fromisoformat(response.get("created_at", "")) if response.get("created_at") else None,
            updated_at=datetime.fromisoformat(response.get("updated_at", "")) if response.get("updated_at") else None,
        )
    
    def get(self, briefcase_id: str) -> Briefcase:
        """Get briefcase information."""
        response = self.get(f"/api/briefcases/{briefcase_id}")
        return Briefcase(
            id=response.get("id", ""),
            name=response.get("name", ""),
            description=response.get("description"),
            case_type=response.get("case_type"),
            status=response.get("status", "active"),
            item_count=response.get("item_count", 0),
            created_at=datetime.fromisoformat(response.get("created_at", "")) if response.get("created_at") else None,
            updated_at=datetime.fromisoformat(response.get("updated_at", "")) if response.get("updated_at") else None,
        )
    
    def list(self) -> List[Briefcase]:
        """List briefcases."""
        response = self.get("/api/briefcases")
        briefcases = []
        for briefcase_data in response.get("briefcases", []):
            briefcases.append(Briefcase(
                id=briefcase_data.get("id", ""),
                name=briefcase_data.get("name", ""),
                description=briefcase_data.get("description"),
                case_type=briefcase_data.get("case_type"),
                status=briefcase_data.get("status", "active"),
                item_count=briefcase_data.get("item_count", 0),
                created_at=datetime.fromisoformat(briefcase_data.get("created_at", "")) if briefcase_data.get("created_at") else None,
                updated_at=datetime.fromisoformat(briefcase_data.get("updated_at", "")) if briefcase_data.get("updated_at") else None,
            ))
        return briefcases


class VaultClient(BaseClient):
    """Vault (secure storage) service client."""
    
    def add_item(self, name: str, item_type: str = "document", 
                 description: Optional[str] = None, access_type: str = "private",
                 tags: Optional[List[str]] = None, encrypt: bool = True) -> VaultItem:
        """Add an item to the vault."""
        data = {
            "name": name,
            "item_type": item_type,
            "access_type": access_type,
            "encrypt": encrypt,
        }
        if description:
            data["description"] = description
        if tags:
            data["tags"] = tags
        
        response = self.post("/api/vault/items", json=data)
        return VaultItem(
            id=response.get("id", ""),
            name=response.get("name", ""),
            item_type=response.get("item_type", ""),
            access_type=response.get("access_type", "private"),
            description=response.get("description"),
            document_id=response.get("document_id"),
            encrypted=response.get("encrypted", True),
            tags=response.get("tags", []),
        )
    
    def get_item(self, item_id: str) -> VaultItem:
        """Get vault item."""
        response = self.get(f"/api/vault/items/{item_id}")
        return VaultItem(
            id=response.get("id", ""),
            name=response.get("name", ""),
            item_type=response.get("item_type", ""),
            access_type=response.get("access_type", "private"),
            description=response.get("description"),
            document_id=response.get("document_id"),
            encrypted=response.get("encrypted", True),
            tags=response.get("tags", []),
        )
    
    def list_items(self, access_type: Optional[str] = None, 
                   item_type: Optional[str] = None, tags: Optional[List[str]] = None,
                   limit: int = 50) -> List[VaultItem]:
        """List vault items."""
        params = {"limit": limit}
        if access_type:
            params["access_type"] = access_type
        if item_type:
            params["item_type"] = item_type
        if tags:
            params["tags"] = ",".join(tags)
        
        response = self.get("/api/vault/items", params=params)
        items = response.get("items", [])
        vault_items = []
        for item_data in items:
            vault_items.append(VaultItem(
                id=item_data.get("id", ""),
                name=item_data.get("name", ""),
                item_type=item_data.get("item_type", ""),
                access_type=item_data.get("access_type", "private"),
                description=item_data.get("description"),
                document_id=item_data.get("document_id"),
                encrypted=item_data.get("encrypted", True),
                tags=item_data.get("tags", []),
            ))
        return vault_items
    
    def delete_item(self, item_id: str) -> bool:
        """Delete vault item."""
        try:
            self.delete(f"/api/vault/items/{item_id}")
            return True
        except Exception:
            return False


# =============================================================================
# MAIN SEMPTIFY CLIENT
# =============================================================================

class SemptifyClient:
    """
    Main Semptify SDK client - Single File Implementation
    
    Provides unified access to all Semptify API services.
    
    Example:
        ```python
        from semptify_sdk import SemptifyClient
        
        # Initialize client
        client = SemptifyClient("http://localhost:8000")
        
        # Authenticate via OAuth
        auth_url = client.auth.get_auth_url("google")
        client.auth.complete_oauth("google", code, state)
        
        # Upload a document
        doc = client.documents.upload("lease.pdf")
        
        # Get AI analysis
        analysis = client.copilot.analyze_case()
        
        # Check deadlines
        deadlines = client.timeline.get_deadlines()
        ```
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        user_id: Optional[str] = None,
    ):
        """Initialize the Semptify client."""
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.user_id = user_id
        
        # Initialize HTTP clients
        self._client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None
        
        # Initialize service clients (lazy)
        self._auth: Optional[AuthClient] = None
        self._documents: Optional[DocumentClient] = None
        self._timeline: Optional[TimelineClient] = None
        self._copilot: Optional[CopilotClient] = None
        self._complaints: Optional[ComplaintClient] = None
        self._briefcase: Optional[BriefcaseClient] = None
        self._vault: Optional[VaultClient] = None
        
        # Current user info
        self._current_user: Optional[UserInfo] = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get default headers for requests."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "Semptify-SDK/5.0.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    @property
    def client(self) -> httpx.Client:
        """Get or create the sync HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers=self._get_headers(),
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client
    
    @property
    def async_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._get_headers(),
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._async_client
    
    def _create_service_client(self, client_class):
        """Create a service client with shared HTTP client."""
        instance = client_class.__new__(client_class)
        instance.base_url = self.base_url
        instance.timeout = self.timeout
        instance.user_id = self.user_id
        instance._client = None
        instance._async_client = None
        # Share the HTTP clients
        instance.client = self.client
        instance.async_client = self.async_client
        return instance
    
    @property
    def auth(self) -> AuthClient:
        """Authentication service client."""
        if self._auth is None:
            self._auth = self._create_service_client(AuthClient)
        return self._auth
    
    @property
    def documents(self) -> DocumentClient:
        """Document management service client."""
        if self._documents is None:
            self._documents = self._create_service_client(DocumentClient)
        return self._documents
    
    @property
    def timeline(self) -> TimelineClient:
        """Timeline and deadline service client."""
        if self._timeline is None:
            self._timeline = self._create_service_client(TimelineClient)
        return self._timeline
    
    @property
    def copilot(self) -> CopilotClient:
        """AI copilot service client."""
        if self._copilot is None:
            self._copilot = self._create_service_client(CopilotClient)
        return self._copilot
    
    @property
    def complaints(self) -> ComplaintClient:
        """Complaint management service client."""
        if self._complaints is None:
            self._complaints = self._create_service_client(ComplaintClient)
        return self._complaints
    
    @property
    def briefcase(self) -> BriefcaseClient:
        """Briefcase management service client."""
        if self._briefcase is None:
            self._briefcase = self._create_service_client(BriefcaseClient)
        return self._briefcase
    
    @property
    def vault(self) -> VaultClient:
        """Vault (secure storage) service client."""
        if self._vault is None:
            self._vault = self._create_service_client(VaultClient)
        return self._vault
    
    @property
    def current_user(self) -> Optional[UserInfo]:
        """Get the current authenticated user."""
        return self._current_user
    
    def login(self, provider: str, code: str, state: str) -> UserInfo:
        """Complete OAuth login."""
        self._current_user = self.auth.complete_oauth(provider, code, state)
        self.user_id = self._current_user.user_id
        return self._current_user
    
    def logout(self) -> bool:
        """Log out the current user."""
        success = self.auth.logout()
        if success:
            self._current_user = None
            self.user_id = None
        return success
    
    def close(self):
        """Close HTTP clients."""
        if self._client:
            self._client.close()
        if self._async_client:
            import asyncio
            if asyncio.get_event_loop().is_running():
                # If in async context, create a task to close
                asyncio.create_task(self._async_client.aclose())
            else:
                # If not in async context, run the coroutine
                asyncio.run(self._async_client.aclose())
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# =============================================================================
# VERSION AND EXPORTS
# =============================================================================

__version__ = "5.0.0"
__all__ = [
    "SemptifyClient",
    "AuthClient",
    "DocumentClient", 
    "TimelineClient",
    "CopilotClient",
    "ComplaintClient",
    "BriefcaseClient",
    "VaultClient",
    "UserInfo",
    "StorageProvider",
    "Document",
    "TimelineEvent",
    "Complaint",
    "Briefcase",
    "VaultItem",
    "SemptifyError",
    "AuthenticationError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "ServerError",
    "StorageRequiredError",
]
