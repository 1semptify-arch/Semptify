"""
Document Delivery Router
=========================
API endpoints for document delivery system.

Routes:
- POST /api/delivery/send - Send document to tenant
- GET /api/delivery/inbox - Get tenant's received documents
- GET /api/delivery/outbox - Get sender's sent documents
- GET /api/delivery/{delivery_id} - View delivery details
- POST /api/delivery/{delivery_id}/sign - Sign a document
- POST /api/delivery/{delivery_id}/reject - Reject a document
- POST /api/delivery/{delivery_id}/viewed - Mark as viewed
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Form, status, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings, Settings
from app.core.security import require_user, StorageUser
from app.core.workflow_engine import route_user
from app.core.navigation import navigation
from app.core.ssot_guard import ssot_redirect
from app.models.document_delivery_models import (
    SendDocumentRequest,
    SendDocumentResponse,
    DeliveryListResponse,
    DeliveryDetailResponse,
    SignDocumentRequest,
    SignDocumentResponse,
    RejectDocumentRequest,
    RejectDocumentResponse,
)
from app.services.document_delivery_service import get_delivery_service

router = APIRouter(prefix="/api/delivery", tags=["Document Delivery"])

# Roles that can send documents
SENDER_ROLES = {"advocate", "manager", "legal", "admin"}


async def get_storage_client(user: StorageUser, db: AsyncSession, settings: Settings):
    """Get cloud storage client for delivery operations."""
    from app.routers.cloud_sync import get_storage_client as get_cloud_storage
    return await get_cloud_storage(user, db, settings)


def _get_user_role(user: StorageUser) -> str:
    """Extract role from user ID."""
    from app.core.user_id import get_role_from_user_id
    return get_role_from_user_id(user.user_id) or "user"


# =============================================================================
# Health Check
# =============================================================================

@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "document_delivery",
        "version": "1.0",
    }


# =============================================================================
# Page Routes (HTML)
# =============================================================================

@router.get("/inbox", response_class=HTMLResponse)
async def delivery_inbox_page(request: Request):
    """
    Serve the tenant document delivery inbox page.
    
    Shows all pending and historical document deliveries with
    signing, rejection, and read receipt capabilities.
    """
    # Check authentication via cookie
    user_id = request.cookies.get("se_user")
    if not user_id:
        # Redirect to storage providers for OAuth
        providers_stage = navigation.get_stage("providers")
        providers_path = providers_stage.path if providers_stage else "/storage/providers"
        return ssot_redirect(providers_path, context="delivery_inbox_page unauthenticated")
    
    # Return the static HTML page
    from pathlib import Path
    html_path = Path("static/delivery_inbox.html")
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    else:
        raise HTTPException(status_code=404, detail="Delivery inbox page not found")


# =============================================================================
# Send Document (Professional → Tenant)
# =============================================================================

@router.post("/send", response_model=SendDocumentResponse)
async def send_document(
    recipient_id: str = Form(..., description="Tenant user ID"),
    document_id: str = Form(..., description="Vault document ID to send"),
    delivery_type: str = Form(..., description="review_required or signature_required"),
    requires_read_receipt: bool = Form(False, description="Require read receipt (review_required only)"),
    message: Optional[str] = Form(None, description="Optional message to recipient"),
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SendDocumentResponse:
    """
    Send a document to a tenant.
    
    Only Advocate, Manager, Legal, and Admin roles can send documents.
    
    Delivery types:
    - `review_required`: Tenant must view; optional read receipt
    - `signature_required`: Tenant must sign or reject
    """
    # Validate role
    sender_role = _get_user_role(user)
    if sender_role not in SENDER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{sender_role}' cannot send documents"
        )
    
    # Get storage client
    storage = await get_storage_client(user, db, settings)
    
    # Get sender info
    sender_name = user.user_id  # Simplified - would normally look up profile
    sender_org = None
    
    # Get recipient name (would normally look up profile)
    recipient_name = recipient_id  # Simplified
    
    # Get document info (would normally fetch from vault)
    document_filename = f"document_{document_id}.pdf"  # Simplified
    document_hash = "placeholder_hash"  # Would compute from actual document
    
    # Build request
    from app.models.document_delivery_models import DeliveryType
    try:
        delivery_type_enum = DeliveryType(delivery_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid delivery_type: {delivery_type}"
        )
    
    request = SendDocumentRequest(
        recipient_id=recipient_id,
        document_id=document_id,
        delivery_type=delivery_type_enum,
        requires_read_receipt=requires_read_receipt,
        message=message,
    )
    
    # Send via service
    service = await get_delivery_service(storage, user.user_id)
    return await service.send_document(
        request=request,
        sender_name=sender_name,
        sender_organization=sender_org,
        sender_role=sender_role,
        recipient_name=recipient_name,
        document_filename=document_filename,
        document_hash=document_hash,
    )


# =============================================================================
# Tenant Inbox
# =============================================================================

@router.get("/inbox", response_model=DeliveryListResponse)
async def get_inbox(
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DeliveryListResponse:
    """
    Get all documents delivered to the current user (tenant inbox).
    
    Returns pending and historical deliveries with status information.
    """
    storage = await get_storage_client(user, db, settings)
    service = await get_delivery_service(storage, user.user_id)
    return await service.get_inbox()


# =============================================================================
# Sender Outbox
# =============================================================================

@router.get("/outbox", response_model=DeliveryListResponse)
async def get_outbox(
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DeliveryListResponse:
    """
    Get all documents sent by the current user (professional outbox).
    
    Only available to Advocate, Manager, Legal, Admin roles.
    """
    # Validate role
    sender_role = _get_user_role(user)
    if sender_role not in SENDER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only professional roles can view outbox"
        )
    
    storage = await get_storage_client(user, db, settings)
    service = await get_delivery_service(storage, user.user_id)
    return await service.get_outbox()


# =============================================================================
# View Delivery Detail
# =============================================================================

@router.get("/{delivery_id}", response_model=DeliveryDetailResponse)
async def get_delivery(
    delivery_id: str,
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DeliveryDetailResponse:
    """
    Get full details of a specific delivery.
    
    Only accessible to sender and recipient.
    """
    storage = await get_storage_client(user, db, settings)
    service = await get_delivery_service(storage, user.user_id)
    
    detail = await service.get_delivery_detail(delivery_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    return detail


# =============================================================================
# Mark Viewed (Read Receipt)
# =============================================================================

@router.post("/{delivery_id}/viewed")
async def mark_viewed(
    delivery_id: str,
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Mark a document as viewed (for read receipt tracking).
    
    Only affects deliveries with `requires_read_receipt=True`.
    """
    storage = await get_storage_client(user, db, settings)
    service = await get_delivery_service(storage, user.user_id)
    
    success = await service.mark_viewed(delivery_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to mark viewed")
    
    return {"success": True, "delivery_id": delivery_id, "viewed": True}


# =============================================================================
# Sign Document
# =============================================================================

@router.post("/{delivery_id}/sign", response_model=SignDocumentResponse)
async def sign_document(
    delivery_id: str,
    request: SignDocumentRequest,
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SignDocumentResponse:
    """
    Sign a document that requires signature.
    
    Only available to the recipient tenant.
    """
    storage = await get_storage_client(user, db, settings)
    service = await get_delivery_service(storage, user.user_id)
    
    return await service.sign_document(delivery_id, request)


# =============================================================================
# Reject Document
# =============================================================================

@router.post("/{delivery_id}/reject", response_model=RejectDocumentResponse)
async def reject_document(
    delivery_id: str,
    request: RejectDocumentRequest,
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RejectDocumentResponse:
    """
    Reject a document that requires signature.
    
    Only available to the recipient tenant.
    Rejection reason is required and stored in audit trail.
    """
    storage = await get_storage_client(user, db, settings)
    service = await get_delivery_service(storage, user.user_id)
    
    return await service.reject_document(delivery_id, request)
