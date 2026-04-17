"""
Phase 2 SDK - Housing Rights Platform Development Kit
==================================================

Comprehensive SDK for Phase 2 advanced features including
document preview, batch operations, security, and testing.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from dataclasses import dataclass
import json
import base64
import io

logger = logging.getLogger(__name__)

@dataclass
class SDKConfig:
    """SDK configuration for Phase 2 features."""
    api_base_url: str
    api_key: str
    timeout: int = 30
    retry_attempts: int = 3
    enable_websockets: bool = True
    enable_2fa: bool = True
    cache_enabled: bool = True

class Phase2SDK:
    """Phase 2 SDK for advanced housing rights platform features."""
    
    def __init__(self, config: SDKConfig):
        self.config = config
        self.session = None
        self.websocket = None
        self.two_factor_enabled = False
        
    async def authenticate(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user with enhanced security."""
        import httpx
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.config.api_base_url}/api/auth/login",
                json={"email": email, "password": password},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if 2FA is required
                if data.get("requires_2fa") and self.config.enable_2fa:
                    return {
                        "success": False,
                        "requires_2fa": True,
                        "message": "Two-factor authentication required"
                    }
                
                self.session = data.get("token")
                return {
                    "success": True,
                    "token": self.session,
                    "user": data.get("user"),
                    "message": "Authentication successful"
                }
            else:
                return {
                    "success": False,
                    "error": "Authentication failed",
                    "status_code": response.status_code
                }
    
    async def setup_2fa(self, method: str = "totp") -> Dict[str, Any]:
        """Setup two-factor authentication."""
        import httpx
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.config.api_base_url}/api/security/2fa/setup",
                json={"method": method},
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.session}"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "qr_code": data.get("qr_code"),
                    "backup_codes": data.get("backup_codes"),
                    "message": "2FA setup successful"
                }
            else:
                return {
                    "success": False,
                    "error": "2FA setup failed",
                    "status_code": response.status_code
                }
    
    async def generate_document_preview(self, document_id: str, 
                                  preview_type: str = "preview",
                                  page_number: int = 1,
                                  max_pages: int = 10) -> Dict[str, Any]:
        """Generate document preview."""
        import httpx
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.config.api_base_url}/api/preview/generate",
                json={
                    "document_id": document_id,
                    "preview_type": preview_type,
                    "page_number": page_number,
                    "max_pages": max_pages
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.session}"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "preview_url": data.get("preview_url"),
                    "metadata": data.get("metadata"),
                    "message": "Preview generated successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Preview generation failed",
                    "status_code": response.status_code
                }
    
    async def create_batch_operation(self, operation_type: str,
                                items: List[Dict[str, Any]],
                                settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create batch operation for document management."""
        import httpx
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.config.api_base_url}/api/batch/create",
                json={
                    "operation_type": operation_type,
                    "items": items,
                    "settings": settings or {}
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.session}"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "operation_id": data.get("operation_id"),
                    "status": data.get("status"),
                    "total_items": data.get("total_items"),
                    "message": "Batch operation created"
                }
            else:
                return {
                    "success": False,
                    "error": "Batch operation creation failed",
                    "status_code": response.status_code
                }
    
    async def export_user_data(self, export_type: str = "all_data",
                           format: str = "json",
                           filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Export user data with GDPR compliance."""
        import httpx
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.config.api_base_url}/api/export-import/export/request",
                json={
                    "export_type": export_type,
                    "format": format,
                    "filters": filters or {}
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.session}"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "export_id": data.get("export_id"),
                    "download_url": data.get("download_url"),
                    "expires_at": data.get("expires_at"),
                    "message": "Export request created"
                }
            else:
                return {
                    "success": False,
                    "error": "Export request failed",
                    "status_code": response.status_code
                }
    
    async def run_automated_tests(self, suite_id: str,
                               test_filter: str = None,
                               environment: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run automated tests."""
        import httpx
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.config.api_base_url}/api/testing/run",
                json={
                    "suite_id": suite_id,
                    "test_filter": test_filter,
                    "environment": environment or {}
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.session}"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "run_id": data.get("run_id"),
                    "status": data.get("status"),
                    "message": "Test run started"
                }
            else:
                return {
                    "success": False,
                    "error": "Test run failed",
                    "status_code": response.status_code
                }
    
    async def connect_websocket(self, channels: List[str] = None) -> bool:
        """Connect to WebSocket for real-time updates."""
        if not self.config.enable_websockets:
            return False
        
        try:
            import websockets
            
            ws_url = f"{self.config.api_base_url.replace('http', 'ws')}/ws/events"
            
            self.websocket = await websockets.connect(
                ws_url,
                extra_headers={"Authorization": f"Bearer {self.session}"}
            )
            
            # Subscribe to channels
            if channels:
                subscribe_message = {
                    "type": "subscribe",
                    "channels": channels
                }
                await self.websocket.send(json.dumps(subscribe_message))
            
            logger.info(f"Connected to WebSocket: {ws_url}")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False
    
    async def listen_for_updates(self, callback=None):
        """Listen for real-time updates via WebSocket."""
        if not self.websocket:
            raise RuntimeError("WebSocket not connected. Call connect_websocket() first.")
        
        try:
            async for message in self.websocket:
                data = json.loads(message)
                
                # Handle different message types
                if data.get("type") == "job_update":
                    if callback:
                        await callback("job_update", data.get("data"))
                
                elif data.get("type") == "batch_operation_update":
                    if callback:
                        await callback("batch_update", data.get("data"))
                
                elif data.get("type") == "security_event":
                    if callback:
                        await callback("security_event", data.get("data"))
                
        except Exception as e:
            logger.error(f"WebSocket listening error: {e}")
    
    async def search_documents(self, query: str,
                          filters: Dict[str, Any] = None,
                          sort_by: str = "relevance",
                          limit: int = 20) -> Dict[str, Any]:
        """Advanced search with BM25 scoring."""
        import httpx
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                f"{self.config.api_base_url}/api/search/advanced",
                params={
                    "q": query,
                    "filters": json.dumps(filters) if filters else None,
                    "sort_by": sort_by,
                    "limit": limit
                },
                headers={"Authorization": f"Bearer {self.session}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "results": data.get("results", []),
                    "total": data.get("total", 0),
                    "search_time": data.get("search_time"),
                    "message": "Search completed successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Search failed",
                    "status_code": response.status_code
                }
    
    async def get_documentation(self, format: str = "openapi") -> Dict[str, Any]:
        """Get API documentation."""
        import httpx
        
        format_endpoints = {
            "openapi": "/api/docs/openapi.json",
            "postman": "/api/docs/postman",
            "swagger": "/api/docs/swagger",
            "redoc": "/api/docs/redoc"
        }
        
        endpoint = format_endpoints.get(format, "/api/docs/openapi.json")
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                f"{self.config.api_base_url}{endpoint}",
                headers={"Authorization": f"Bearer {self.session}"}
            )
            
            if response.status_code == 200:
                if format == "openapi":
                    return {
                        "success": True,
                        "spec": response.json(),
                        "message": "OpenAPI specification retrieved"
                    }
                else:
                    return {
                        "success": True,
                        "documentation_url": f"{self.config.api_base_url}{endpoint}",
                        "message": f"{format.upper()} documentation retrieved"
                    }
            else:
                return {
                    "success": False,
                    "error": "Documentation retrieval failed",
                    "status_code": response.status_code
                }

class HousingRightsSDK(Phase2SDK):
    """Specialized SDK for housing rights applications."""
    
    def __init__(self, config: SDKConfig):
        super().__init__(config)
        self.housing_context = {}
    
    async def process_evidence_document(self, document_id: str,
                                   evidence_type: str = "lease_violation") -> Dict[str, Any]:
        """Process housing evidence document with legal context."""
        # Generate preview with housing-specific metadata
        preview_result = await self.generate_document_preview(
            document_id=document_id,
            preview_type="preview",
            max_pages=5  # Limit for legal documents
        )
        
        if preview_result["success"]:
            # Add housing rights context
            housing_metadata = {
                "evidence_type": evidence_type,
                "legal_categories": self._get_legal_categories(evidence_type),
                "urgency": self._assess_urgency(evidence_type),
                "jurisdiction": "minnesota",  # Default jurisdiction
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            
            preview_result["housing_metadata"] = housing_metadata
            preview_result["message"] = "Evidence document processed for housing rights context"
        
        return preview_result
    
    def _get_legal_categories(self, evidence_type: str) -> List[str]:
        """Get legal categories for evidence type."""
        categories = {
            "lease_violation": ["lease_terms", "maintenance", "habitability", "retaliation"],
            "eviction_notice": ["notice_period", "grounds", "procedures", "defenses"],
            "maintenance_issue": ["habitability", "repair_requests", "rent_withholding", "code_compliance"],
            "discrimination": ["fair_housing", "disability_rights", "familial_status"],
            "security_deposit": ["return_conditions", "itemized_deductions", "interest_requirements"],
            "court_filing": ["eviction_defense", "small_claims", "evidence_submission"]
        }
        
        return categories.get(evidence_type, ["general"])
    
    def _assess_urgency(self, evidence_type: str) -> str:
        """Assess urgency level for evidence type."""
        urgency_map = {
            "eviction_notice": "critical",
            "court_filing": "critical",
            "lease_violation": "high",
            "maintenance_issue": "medium",
            "discrimination": "high",
            "security_deposit": "low"
        }
        
        return urgency_map.get(evidence_type, "medium")
    
    async def create_legal_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a legal case with housing rights context."""
        # Validate case data for housing rights
        required_fields = ["case_type", "parties", "jurisdiction"]
        for field in required_fields:
            if field not in case_data:
                return {
                    "success": False,
                    "error": f"Missing required field: {field}",
                    "message": "Legal case requires all required fields"
                }
        
        # Add housing rights metadata
        case_data["housing_rights_context"] = {
            "case_category": self._get_case_category(case_data.get("case_type")),
            "tenant_protections": self._get_tenant_protections(case_data.get("case_type")),
            "landlord_obligations": self._get_landlord_obligations(case_data.get("case_type")),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Create batch operation for case processing
        batch_items = [{
            "type": "legal_case",
            "data": case_data
        }]
        
        return await self.create_batch_operation(
            operation_type="legal_case_processing",
            items=batch_items,
            settings={"priority": "high", "housing_rights": True}
        )
    
    def _get_case_category(self, case_type: str) -> str:
        """Get housing rights category for case type."""
        category_map = {
            "eviction": "housing_dispute",
            "lease_violation": "contract_dispute",
            "maintenance": "habitability_issue",
            "discrimination": "fair_housing_violation",
            "security_deposit": "financial_dispute"
        }
        
        return category_map.get(case_type, "general_housing")
    
    def _get_tenant_protections(self, case_type: str) -> List[str]:
        """Get tenant protections for case type."""
        protections = {
            "eviction": ["notice_period", "court_hearing", "legal_representation"],
            "lease_violation": ["implied_warranty", "quiet_enjoyment", "repair_deductions"],
            "maintenance": ["habitability_standards", "repair_timeline", "rent_withholding_rights"],
            "discrimination": ["protected_classes", "reasonable_accommodation", "retaliation_protection"],
            "security_deposit": ["return_deadline", "itemized_statement", "interest_protection"]
        }
        
        return protections.get(case_type, ["general_protection"])
    
    def _get_landlord_obligations(self, case_type: str) -> List[str]:
        """Get landlord obligations for case type."""
        obligations = {
            "eviction": ["proper_notice", "court_filing", "legal_process"],
            "lease_violation": ["maintain_property", "respect_privacy", "perform_repairs"],
            "maintenance": ["timely_repairs", "habitability_compliance", "health_safety"],
            "discrimination": ["equal_treatment", "accommodation_request", "no_retaliation"],
            "security_deposit": ["proper_handling", "itemized_accounting", "timely_return"]
        }
        
        return obligations.get(case_type, ["general_obligation"])

# Factory functions
def create_sdk(api_base_url: str, api_key: str, **kwargs) -> Phase2SDK:
    """Create Phase 2 SDK instance."""
    config = SDKConfig(
        api_base_url=api_base_url,
        api_key=api_key,
        **kwargs
    )
    return Phase2SDK(config)

def create_housing_sdk(api_base_url: str, api_key: str, **kwargs) -> HousingRightsSDK:
    """Create Housing Rights SDK instance."""
    config = SDKConfig(
        api_base_url=api_base_url,
        api_key=api_key,
        **kwargs
    )
    return HousingRightsSDK(config)

# Example usage
async def example_usage():
    """Example usage of Phase 2 SDK."""
    
    # Initialize SDK
    sdk = create_sdk(
        api_base_url="https://api.semptify.org",
        api_key="your-api-key",
        enable_websockets=True,
        enable_2fa=True
    )
    
    # Authenticate with 2FA
    auth_result = await sdk.authenticate("user@example.com", "password")
    if auth_result["success"]:
        print("Authentication successful")
        
        # Setup 2FA if needed
        if auth_result.get("requires_2fa"):
            totp_result = await sdk.setup_2fa("totp")
            if totp_result["success"]:
                print("2FA setup successful")
                print(f"QR Code: {totp_result['qr_code']}")
        
        # Generate document preview
        preview_result = await sdk.generate_document_preview("doc-123")
        if preview_result["success"]:
            print(f"Preview URL: {preview_result['preview_url']}")
        
        # Create batch operation
        batch_result = await sdk.create_batch_operation(
            operation_type="upload",
            items=[
                {"type": "document", "data": {"filename": "lease.pdf"}},
                {"type": "document", "data": {"filename": "notice.pdf"}}
            ]
        )
        if batch_result["success"]:
            print(f"Batch operation ID: {batch_result['operation_id']}")
        
        # Connect to WebSocket
        if await sdk.connect_websocket(["job_updates", "batch_operations"]):
            print("WebSocket connected")
            
            # Listen for updates
            async def handle_update(update_type, data):
                print(f"Update: {update_type} - {data}")
            
            await sdk.listen_for_updates(handle_update)
    
    else:
        print(f"Authentication failed: {auth_result['error']}")

if __name__ == "__main__":
    asyncio.run(example_usage())
