"""
Unified Overlays Router
=======================
API endpoints for the unified overlay system.

All endpoints are stateless - overlays stored in user's cloud storage only.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header, Cookie, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings, Settings
from app.core.security import require_user, StorageUser, verify_function_token_for_operation
from app.core.overlay_types import OverlayType
from app.models.unified_overlay_models import (
    CreateOverlayRequest,
    CreateOverlayResponse,
    GetOverlaysResponse,
    UpdateOverlayRequest,
    DeleteOverlayResponse,
    DocumentViewResponse,
)
from app.services.unified_overlay_manager import (
    UnifiedOverlayManager,
    get_unified_overlay_manager,
)

router = APIRouter(prefix="/api/unified-overlays", tags=["Unified Overlays"])


# =============================================================================
# Authentication Helper
# =============================================================================

async def require_overlay_access(
    request: Request,
    document_id: Optional[str] = None,
    function_token_header: Optional[str] = Header(None, alias="X-Function-Token"),
    semptify_uid: Optional[str] = Cookie(None),
) -> tuple[str, str, Optional[str]]:
    """
    Require both auth cookie identity and valid function token.
    
    Returns: (user_id, role, token)
    """
    if not semptify_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication cookie required",
        )
    
    token = function_token_header
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Function token required",
        )
    
    action = "overlay:read" if request.method in {"GET", "HEAD", "OPTIONS"} else "overlay:write"
    token_result = verify_function_token_for_operation(
        semptify_uid,
        token,
        action=action,
        document_id=document_id,
        refresh=False,
    )
    
    if not token_result.get("valid"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "function_token_invalid",
                "reason": token_result.get("reason", "invalid"),
                "message": "Function token invalid or expired",
            },
        )
    
    # Get role from user_id
    from app.core.user_id import get_role_from_user_id
    role = get_role_from_user_id(semptify_uid) or "user"
    
    return semptify_uid, role, token


async def get_storage_client(user: StorageUser, db: AsyncSession, settings: Settings):
    """Get cloud storage client for overlay operations."""
    from app.routers.cloud_sync import get_storage_client as get_cloud_storage
    return await get_cloud_storage(user, db, settings)


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "unified_overlays",
        "version": "1.0",
    }


@router.post("/create", response_model=CreateOverlayResponse)
async def create_overlay(
    request: CreateOverlayRequest,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CreateOverlayResponse:
    """
    Create a new overlay for a document.
    
    The overlay is stored in user's cloud storage, not on Semptify servers.
    """
    # Verify user has access to the document
    auth_user_id, _, _ = await require_overlay_access(
        Request(scope={"type": "http"}),
        document_id=request.document_id,
        function_token_header=None,
        semptify_uid=user.user_id,
    )
    
    storage = await get_storage_client(user, db, settings)
    manager = await get_unified_overlay_manager(storage, user.user_id)
    
    return await manager.create_overlay(request)


@router.get("/list", response_model=GetOverlaysResponse)
async def list_overlays(
    document_id: Optional[str] = None,
    overlay_type: Optional[OverlayType] = None,
    category: Optional[str] = None,
    include_ephemeral: bool = False,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> GetOverlaysResponse:
    """
    List overlays for the authenticated user.
    
    Filters:
    - document_id: Filter by specific document
    - overlay_type: Filter by overlay type
    - category: Filter by category (upload, processing, annotation, form, query, redaction)
    - include_ephemeral: Include ephemeral overlays (default: false)
    """
    storage = await get_storage_client(user, db, settings)
    manager = await get_unified_overlay_manager(storage, user.user_id)
    
    return await manager.get_overlays(
        document_id=document_id,
        overlay_type=overlay_type,
        category=category,
        created_by=user.user_id,
        include_ephemeral=include_ephemeral,
    )


@router.get("/{overlay_id}")
async def get_overlay(
    overlay_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Get a specific overlay by ID."""
    storage = await get_storage_client(user, db, settings)
    manager = await get_unified_overlay_manager(storage, user.user_id)
    
    overlay = await manager.get_overlay(overlay_id)
    if not overlay:
        raise HTTPException(status_code=404, detail="Overlay not found")
    
    # Verify ownership
    if overlay.created_by != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "success": True,
        "overlay": overlay.dict(),
    }


@router.patch("/{overlay_id}")
async def update_overlay(
    overlay_id: str,
    request: UpdateOverlayRequest,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Update an existing overlay."""
    storage = await get_storage_client(user, db, settings)
    manager = await get_unified_overlay_manager(storage, user.user_id)
    
    success = await manager.update_overlay(
        overlay_id,
        payload=request.payload,
        metadata=request.metadata,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update overlay")
    
    return {
        "success": True,
        "overlay_id": overlay_id,
        "message": "Overlay updated successfully",
    }


@router.delete("/{overlay_id}", response_model=DeleteOverlayResponse)
async def delete_overlay(
    overlay_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DeleteOverlayResponse:
    """Delete an overlay."""
    storage = await get_storage_client(user, db, settings)
    manager = await get_unified_overlay_manager(storage, user.user_id)
    
    success = await manager.delete_overlay(overlay_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete overlay")
    
    return DeleteOverlayResponse(
        success=True,
        overlay_id=overlay_id,
        message="Overlay deleted successfully",
    )


@router.post("/compose-view", response_model=DocumentViewResponse)
async def compose_document_view(
    document_id: str,
    overlay_ids: list[str],
    apply_redactions: bool = True,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DocumentViewResponse:
    """
    Compose a view of a document with overlays applied.
    
    This returns a view specification - no file is created.
    The view can be rendered on-demand with watermarks if needed.
    """
    storage = await get_storage_client(user, db, settings)
    manager = await get_unified_overlay_manager(storage, user.user_id)
    
    return await manager.compose_document_view(
        document_id=document_id,
        overlay_ids=overlay_ids,
        apply_redactions=apply_redactions,
    )


# =============================================================================
# Type-Specific Convenience Endpoints
# =============================================================================

@router.post("/annotations/highlight")
async def add_highlight(
    document_id: str,
    vault_path: str,
    range_data: dict,  # TextRange as dict
    color: str = "yellow",
    note: Optional[str] = None,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CreateOverlayResponse:
    """Convenience endpoint to add a highlight overlay."""
    from app.models.unified_overlay_models import HighlightPayload
    
    payload = HighlightPayload(
        range=range_data,
        color=color,
        note=note,
    ).dict()
    
    request = CreateOverlayRequest(
        overlay_type=OverlayType.HIGHLIGHT,
        document_id=document_id,
        vault_path=vault_path,
        payload=payload,
    )
    
    storage = await get_storage_client(user, db, settings)
    manager = await get_unified_overlay_manager(storage, user.user_id)
    
    return await manager.create_overlay(request)


@router.post("/annotations/note")
async def add_note(
    document_id: str,
    vault_path: str,
    content: str,
    range_data: Optional[dict] = None,
    note_type: str = "user",
    priority: str = "normal",
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CreateOverlayResponse:
    """Convenience endpoint to add a note overlay."""
    from app.models.unified_overlay_models import NotePayload, TextRange
    
    payload = NotePayload(
        range=TextRange(**range_data) if range_data else None,
        content=content,
        note_type=note_type,
        priority=priority,
    ).dict()
    
    request = CreateOverlayRequest(
        overlay_type=OverlayType.NOTE,
        document_id=document_id,
        vault_path=vault_path,
        payload=payload,
    )
    
    storage = await get_storage_client(user, db, settings)
    manager = await get_unified_overlay_manager(storage, user.user_id)
    
    return await manager.create_overlay(request)
