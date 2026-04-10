from fastapi import APIRouter, HTTPException, Request

from app.core.audit import AuditAction, audit_log
from app.core.event_bus import EventType, event_bus
from app.core.security import (
    get_function_token_user_id,
    verify_function_token_for_operation,
)
from app.core.user_id import get_role_from_user_id
from app.models.document_overlay_models import (
    DocumentOverlayApplyRequest,
    DocumentOverlayCreate,
)
from app.services.document_overlay_service import document_overlay_service


router = APIRouter(prefix="/api/document-overlays", tags=["Document Overlays v2"])

_WRITE_ROLES = {"advocate", "manager", "legal", "admin"}
_READ_ROLES = _WRITE_ROLES | {"user"}


def _resolve_auth(
    request: Request,
    allowed_roles: set[str],
    action: str,
    document_id: str | None = None,
) -> tuple[str, str, str | None]:
    """
    Authenticate the request using Bearer token (header-only) or cookie fallback.

    Bearer flow: validates function access token, enforces scope (action) and,
    when document_id is supplied, the per-document constraint from the token context.

    Cookie flow: validates semptify_uid cookie and checks role membership.

    Returns (user_id, role, raw_bearer_token_or_None).
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        raw_token = auth_header[7:]
        user_id = get_function_token_user_id(raw_token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        result = verify_function_token_for_operation(
            user_id, raw_token, action, document_id=document_id
        )
        if not result.get("valid"):
            raise HTTPException(
                status_code=403,
                detail=result.get("reason", "token_invalid"),
            )
        return user_id, get_role_from_user_id(user_id) or "user", raw_token

    # Cookie fallback
    user_id = request.cookies.get("semptify_uid")
    role = get_role_from_user_id(user_id)
    if not user_id or role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient role privileges")
    return user_id, role, None


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "document_overlays_v2"}


@router.post("/records")
async def create_overlay_record(payload: DocumentOverlayCreate, request: Request) -> dict:
    user_id, _, _ = _resolve_auth(request, _WRITE_ROLES, "overlay:write", document_id=payload.document_id)
    record = document_overlay_service.create_overlay(payload)

    try:
        await audit_log(
            action=AuditAction.CONFIG_CHANGE,
            user_id=user_id,
            resource_type="document_overlay",
            resource_id=record.overlay_id,
            details={
                "document_id": record.document_id,
                "overlay_type": record.overlay_type,
                "status": record.status,
            },
        )
    except Exception:
        pass

    try:
        event_bus.publish_sync(
            EventType.USER_ACTION,
            {
                "feature": "document_overlays",
                "action": "overlay_record_created",
                "overlay_id": record.overlay_id,
                "document_id": record.document_id,
            },
            source="document_overlays_router",
            user_id=user_id,
        )
    except Exception:
        pass

    return record.model_dump()


@router.get("/records")
async def list_overlay_records(
    request: Request,
    document_id: str | None = None,
    vault_id: str | None = None,
) -> list[dict]:
    _resolve_auth(request, _READ_ROLES, "overlay:read", document_id=document_id)
    records = document_overlay_service.list_overlays(document_id=document_id, vault_id=vault_id)
    return [record.model_dump() for record in records]


@router.get("/records/{overlay_id}")
async def get_overlay_record(overlay_id: str, request: Request) -> dict:
    # Phase 1: validate token/role without doc constraint (overlay_id not yet resolved)
    user_id, _, raw_token = _resolve_auth(request, _READ_ROLES, "overlay:read")
    record = document_overlay_service.get_overlay(overlay_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Overlay record not found")
    # Phase 2: enforce document constraint for Bearer token holders
    if raw_token:
        doc_result = verify_function_token_for_operation(
            user_id, raw_token, "overlay:read", document_id=record.document_id
        )
        if not doc_result.get("valid"):
            raise HTTPException(status_code=403, detail=doc_result.get("reason", "token_document_denied"))
    return record.model_dump()


@router.post("/records/{overlay_id}/apply")
async def apply_overlay_record(
    overlay_id: str,
    payload: DocumentOverlayApplyRequest,
    request: Request,
) -> dict:
    # Phase 1: validate token/role without doc constraint (overlay not yet looked up)
    user_id, _, raw_token = _resolve_auth(request, _WRITE_ROLES, "overlay:write")
    # Look up overlay before applying — also needed for doc constraint check
    pre_check = document_overlay_service.get_overlay(overlay_id)
    if pre_check is None:
        raise HTTPException(status_code=404, detail="Overlay record not found")
    # Phase 2: enforce document constraint for Bearer token holders
    if raw_token:
        doc_result = verify_function_token_for_operation(
            user_id, raw_token, "overlay:write", document_id=pre_check.document_id
        )
        if not doc_result.get("valid"):
            raise HTTPException(status_code=403, detail=doc_result.get("reason", "token_document_denied"))
    result = document_overlay_service.apply_overlay(overlay_id, dry_run=payload.dry_run)
    if result is None:
        raise HTTPException(status_code=404, detail="Overlay record not found")

    if not payload.dry_run:
        try:
            await audit_log(
                action=AuditAction.CONFIG_CHANGE,
                user_id=user_id,
                resource_type="document_overlay",
                resource_id=overlay_id,
                details={"operation": "apply", "status": result.status},
            )
        except Exception:
            pass

        try:
            event_bus.publish_sync(
                EventType.USER_ACTION,
                {
                    "feature": "document_overlays",
                    "action": "overlay_record_applied",
                    "overlay_id": overlay_id,
                },
                source="document_overlays_router",
                user_id=user_id,
            )
        except Exception:
            pass

    return result.model_dump()
