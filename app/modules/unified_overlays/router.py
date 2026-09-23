"""
Unified Overlays Router
=======================
API endpoints for the unified overlay system.

All endpoints are stateless - overlays stored in user's cloud storage only.
"""

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.overlay_types import OverlayType
from app.core.security import StorageUser, verify_function_token_for_operation, yellow_access
from app.models.unified_overlay_models import (
    CreateOverlayRequest,
    CreateOverlayResponse,
    DeleteOverlayResponse,
    DocumentViewResponse,
    GetOverlaysResponse,
    UpdateOverlayRequest,
)
from app.services.unified_overlay_manager import (
    get_unified_overlay_manager,
)

router = APIRouter(prefix="/api/unified-overlays", tags=["Unified Overlays"])


# =============================================================================
# Authentication Helper
# =============================================================================


async def require_overlay_access(
    request: Request,
    document_id: str | None = None,
    function_token_header: str | None = Header(None, alias="X-Function-Token"),
    semptify_uid: str | None = Cookie(None),
) -> tuple[str, str, str | None]:
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
    from app.modules.cloud_sync.router import get_storage_client as get_cloud_storage

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
    user: StorageUser = Depends(yellow_access),
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
    document_id: str | None = None,
    overlay_type: OverlayType | None = None,
    category: str | None = None,
    include_ephemeral: bool = False,
    user: StorageUser = Depends(yellow_access),
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
    user: StorageUser = Depends(yellow_access),
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
    user: StorageUser = Depends(yellow_access),
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
    user: StorageUser = Depends(yellow_access),
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
    user: StorageUser = Depends(yellow_access),
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
    note: str | None = None,
    user: StorageUser = Depends(yellow_access),
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
    range_data: dict | None = None,
    note_type: str = "user",
    priority: str = "normal",
    user: StorageUser = Depends(yellow_access),
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


@router.post("/annotations/footnote")
async def add_footnote(
    document_id: str,
    vault_path: str,
    number: int,
    range_data: dict,
    content: str,
    citation: str | None = None,
    user: StorageUser = Depends(yellow_access),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CreateOverlayResponse:
    """Convenience endpoint to add a numbered footnote anchored to text."""
    from app.models.unified_overlay_models import FootnotePayload, TextRange

    payload = FootnotePayload(
        number=number,
        range=TextRange(**range_data),
        content=content,
        citation=citation,
    ).dict()

    request = CreateOverlayRequest(
        overlay_type=OverlayType.FOOTNOTE,
        document_id=document_id,
        vault_path=vault_path,
        payload=payload,
    )

    storage = await get_storage_client(user, db, settings)
    manager = await get_unified_overlay_manager(storage, user.user_id)

    return await manager.create_overlay(request)


# =============================================================================
# Document Color Key (DOCUMENT_KEY overlay)
# =============================================================================

DEFAULT_COLOR_KEY: dict[str, str] = {
    "yellow": "Key evidence",
    "red": "Contradiction",
    "blue": "Date or deadline",
    "green": "Money",
    "orange": "Notice or warning",
    "purple": "Personal note",
}

ALLOWED_KEY_COLORS = set(DEFAULT_COLOR_KEY)


@router.get("/annotations/color-key")
async def get_color_key(
    document_id: str,
    user: StorageUser = Depends(yellow_access),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Get a document's color key — colors mapped to plain-English meanings.

    Returns the stored DOCUMENT_KEY overlay if one exists, otherwise the
    default palette so callers can render a legend immediately.
    """
    storage = await get_storage_client(user, db, settings)
    manager = await get_unified_overlay_manager(storage, user.user_id)

    result = await manager.get_overlays(
        document_id=document_id,
        overlay_type=OverlayType.DOCUMENT_KEY,
        created_by=user.user_id,
    )

    for overlay in result.overlays:
        colors = (overlay.payload or {}).get("colors")
        if isinstance(colors, dict):
            merged = {**DEFAULT_COLOR_KEY, **{k: str(v) for k, v in colors.items() if k in ALLOWED_KEY_COLORS}}
            return {
                "success": True,
                "document_id": document_id,
                "overlay_id": overlay.overlay_id,
                "colors": merged,
                "is_default": False,
            }

    return {
        "success": True,
        "document_id": document_id,
        "overlay_id": None,
        "colors": DEFAULT_COLOR_KEY,
        "is_default": True,
    }


@router.put("/annotations/color-key")
async def set_color_key(
    document_id: str,
    vault_path: str,
    key_data: dict,  # {"colors": {yellow: "...", ...}}
    user: StorageUser = Depends(yellow_access),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Create or update a document's color key (upsert).

    Stored as a DOCUMENT_KEY overlay in the user's cloud vault — the original
    document is never modified.
    """
    raw = (key_data or {}).get("colors") or {}
    colors = {
        str(k): str(v).strip()
        for k, v in raw.items()
        if k in ALLOWED_KEY_COLORS and str(v).strip()
    }
    if not colors:
        raise HTTPException(status_code=400, detail="At least one color meaning is required")

    storage = await get_storage_client(user, db, settings)
    manager = await get_unified_overlay_manager(storage, user.user_id)

    existing = await manager.get_overlays(
        document_id=document_id,
        overlay_type=OverlayType.DOCUMENT_KEY,
        created_by=user.user_id,
    )

    if existing.overlays:
        overlay_id = existing.overlays[0].overlay_id
        ok = await manager.update_overlay(
            overlay_id,
            payload={"colors": colors},
        )
        if not ok:
            raise HTTPException(status_code=400, detail="Failed to update color key")
        return {
            "success": True,
            "document_id": document_id,
            "overlay_id": overlay_id,
            "colors": colors,
            "updated": True,
        }

    response = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.DOCUMENT_KEY,
            document_id=document_id,
            vault_path=vault_path,
            payload={"colors": colors},
        )
    )
    return {
        "success": response.success,
        "document_id": document_id,
        "overlay_id": response.overlay_id,
        "colors": colors,
        "updated": False,
    }
