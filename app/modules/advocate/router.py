"""
Advocate API Router
===================

Endpoints for advocate case management:
- GET  /api/advocate/dashboard — aggregate stats across all clients
- GET  /api/advocate/clients — list clients linked to current advocate
- GET  /api/advocate/clients/{client_id} — client detail + stats
- GET  /api/advocate/queue — case queue across all clients
- POST /api/advocate/intake — link a new client
- GET  /api/advocate/timeline — merged multi-tenant timeline
- GET  /api/advocate/clients/{client_id}/documents — client's documents
- POST /api/advocate/clients/{client_id}/documents/{doc_id}/review — mark reviewed

All endpoints require advocate role (verified via user_id cookie).
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.core.database import get_db_session
from app.core.request_utils import require_request_user_id
from app.core.user_context import UserRole, get_role_from_user_id
from app.core.user_id import get_provider_from_user_id
from app.core.utc import utc_now
from app.models.models import (
    Document,
    DocumentAccessLog,
    RelationshipType,
    User,
    UserRelationship,
)
from app.services.timeline_store import count_events_for_user_id, list_events_for_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/advocate", tags=["Advocate"])


# =============================================================================
# Helpers
# =============================================================================


def _require_advocate(user_id: str) -> None:
    """Verify the current user has advocate role."""
    role = get_role_from_user_id(user_id)
    if role not in (UserRole.ADVOCATE, UserRole.MULTI_CLIENT_ADVOCATE, UserRole.ADMIN):
        raise HTTPException(
            status_code=403,
            detail="Only advocates can access this endpoint.",
        )


async def _get_clients_for_advocate(db, advocate_id: str):
    """Return all active ADVOCACY relationships for this advocate."""
    result = await db.execute(
        select(UserRelationship).where(
            UserRelationship.from_user_id == advocate_id,
            UserRelationship.relationship_type == RelationshipType.ADVOCACY.value,
            UserRelationship.is_active.is_(True),
        )
    )
    return result.scalars().all()


async def _check_client_link(db, advocate_id: str, client_id: str) -> UserRelationship:
    """Verify advocate has access to this client. Returns the relationship."""
    result = await db.execute(
        select(UserRelationship).where(
            UserRelationship.from_user_id == advocate_id,
            UserRelationship.to_user_id == client_id,
            UserRelationship.relationship_type == RelationshipType.ADVOCACY.value,
            UserRelationship.is_active.is_(True),
        )
    )
    rel = result.scalars().first()
    if not rel:
        raise HTTPException(
            status_code=403,
            detail="No active advocacy relationship with this client.",
        )
    return rel


def _advocate_visible_doc_stmt(client_id: str):
    """Documents an advocate may see for a client.

    Privileged documents (`is_privileged`) are visible only to the client
    and the creating attorney; attorney work product (`is_work_product`)
    is protected from discovery. Neither is ever exposed to an advocate.
    """
    return select(Document).where(
        Document.user_id == client_id,
        Document.is_privileged.is_(False),
        Document.is_work_product.is_(False),
    )


async def _doc_count(db, tenant_id: str) -> int:
    """Count of advocate-visible documents for a tenant."""
    return (
        await db.execute(
            select(func.count(Document.id)).where(
                Document.user_id == tenant_id,
                Document.is_privileged.is_(False),
                Document.is_work_product.is_(False),
            )
        )
    ).scalar_one()


async def _log_doc_access(
    db,
    actor_user_id: str,
    tenant_user_id: str,
    action: str,
    document_id: str | None = None,
    outcome: str = "ok",
    detail: str | None = None,
) -> None:
    """Append-only audit row for cross-party document access."""
    role = get_role_from_user_id(actor_user_id)
    db.add(
        DocumentAccessLog(
            actor_user_id=actor_user_id,
            actor_role=role.value if role else None,
            tenant_user_id=tenant_user_id,
            document_id=document_id,
            action=action,
            outcome=outcome,
            detail=(detail or "")[:500] or None,
        )
    )
    await db.commit()


async def _check_client_link_logged(db, advocate_id: str, client_id: str, action_hint: str):
    """Client-link check that records denied access attempts (append-only log)."""
    try:
        return await _check_client_link(db, advocate_id, client_id)
    except HTTPException:
        await _log_doc_access(
            db, advocate_id, client_id, "access_denied",
            outcome="denied", detail=action_hint,
        )
        raise


# =============================================================================
# Request Models
# =============================================================================


class IntakeRequest(BaseModel):
    tenant_user_id: str = Field(..., min_length=8, max_length=128, description="Tenant's user_id")
    notes: str | None = Field(default=None, max_length=500, description="Optional intake notes")


class ReviewRequest(BaseModel):
    status: str = Field(default="reviewed", description="Review status: reviewed, flagged, approved")
    notes: str | None = Field(default=None, max_length=500, description="Review notes")


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/dashboard")
async def advocate_dashboard(request: Request):
    """Aggregate dashboard across all linked clients.

    Returns counts, recent activity, urgent cases, and workload summary
    for the advocate's home screen.
    """
    user_id = require_request_user_id(request)
    _require_advocate(user_id)

    async with get_db_session() as db:
        rels = await _get_clients_for_advocate(db, user_id)
        total_clients = len(rels)
        total_docs = 0
        total_events = 0
        pending_reviews = 0
        flagged_docs = 0
        recent_clients = []

        for rel in rels:
            tenant = await db.get(User, rel.to_user_id)
            if not tenant:
                continue
            doc_count = await _doc_count(db, tenant.id)
            event_count = await count_events_for_user_id(tenant.id)
            total_docs += doc_count
            total_events += event_count

            # Count pending reviews and flagged docs from relationship context
            ctx = dict(rel.context) if rel.context else {}
            reviews = ctx.get("document_reviews", {})
            for r in reviews.values():
                if r.get("status") == "flagged":
                    flagged_docs += 1
                elif r.get("status") == "reviewed":
                    pass
                else:
                    pending_reviews += 1

            recent_clients.append(
                {
                    "user_id": tenant.id,
                    "primary_provider": tenant.primary_provider,
                    "doc_count": doc_count,
                    "event_count": event_count,
                    "linked_at": rel.created_at.isoformat() if rel.created_at else None,
                }
            )

        # Sort by linked_at desc, take 5
        recent_clients.sort(key=lambda c: c.get("linked_at") or "", reverse=True)
        recent_clients = recent_clients[:5]

        return {
            "advocate_id": user_id,
            "summary": {
                "total_clients": total_clients,
                "total_documents": total_docs,
                "total_timeline_events": total_events,
                "pending_reviews": pending_reviews,
                "flagged_documents": flagged_docs,
            },
            "recent_clients": recent_clients,
            "generated_at": utc_now().isoformat(),
        }


@router.get("/clients")
async def list_clients(request: Request):
    """List all clients linked to the current advocate."""
    user_id = require_request_user_id(request)
    _require_advocate(user_id)

    async with get_db_session() as db:
        rels = await _get_clients_for_advocate(db, user_id)
        clients = []
        for rel in rels:
            tenant = await db.get(User, rel.to_user_id)
            if not tenant:
                continue
            doc_count = await _doc_count(db, tenant.id)
            event_count = await count_events_for_user_id(tenant.id)
            clients.append(
                {
                    "user_id": tenant.id,
                    "primary_provider": tenant.primary_provider,
                    "doc_count": doc_count,
                    "event_count": event_count,
                    "linked_at": rel.created_at.isoformat() if rel.created_at else None,
                    "context": rel.context,
                }
            )
        return {"advocate_id": user_id, "clients": clients, "count": len(clients)}


@router.get("/clients/{client_id}")
async def client_detail(client_id: str, request: Request):
    """Get a single client's profile and stats."""
    user_id = require_request_user_id(request)
    _require_advocate(user_id)

    async with get_db_session() as db:
        await _check_client_link_logged(db, user_id, client_id, "client_detail")
        tenant = await db.get(User, client_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Client not found")

        doc_count = await _doc_count(db, tenant.id)
        event_count = await count_events_for_user_id(tenant.id)
        recent_events = sorted(
            await list_events_for_user_id(tenant.id),
            key=lambda e: e.created_at or utc_now(),
            reverse=True,
        )[:5]

        return {
            "client": {
                "user_id": tenant.id,
                "primary_provider": tenant.primary_provider,
                "default_role": tenant.default_role,
                "intensity_level": tenant.intensity_level,
                "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
                "last_login": tenant.last_login.isoformat() if tenant.last_login else None,
            },
            "stats": {
                "doc_count": doc_count,
                "event_count": event_count,
            },
            "recent_events": [
                {
                    "id": e.id,
                    "title": getattr(e, "title", None) or getattr(e, "description", ""),
                    "event_date": e.event_date.isoformat() if getattr(e, "event_date", None) else None,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in recent_events
            ],
        }


@router.get("/queue")
async def case_queue(request: Request):
    """Get case queue across all linked clients, sorted by urgency and recency."""
    user_id = require_request_user_id(request)
    _require_advocate(user_id)

    async with get_db_session() as db:
        rels = await _get_clients_for_advocate(db, user_id)
        if not rels:
            return {"queue": [], "count": 0}

        client_ids = [r.to_user_id for r in rels]
        # Get recent events across all clients
        events = []
        for cid in client_ids:
            events.extend(await list_events_for_user_id(cid))
        events.sort(key=lambda e: e.created_at or utc_now(), reverse=True)
        events = events[:50]

        queue = []
        for e in events:
            title = getattr(e, "title", None) or getattr(e, "description", "")
            severity = getattr(e, "severity", "normal")
            queue.append(
                {
                    "client_id": e.user_id,
                    "event_id": e.id,
                    "title": title,
                    "severity": severity,
                    "event_date": e.event_date.isoformat() if getattr(e, "event_date", None) else None,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                    "urgent": severity in ("high", "urgent", "critical"),
                }
            )

        # Sort: urgent first, then by created_at desc
        queue.sort(key=lambda x: (not x["urgent"], x["created_at"] or ""), reverse=False)
        queue.sort(key=lambda x: x["urgent"], reverse=True)

        return {"queue": queue, "count": len(queue)}


@router.post("/intake")
async def new_intake(body: IntakeRequest, request: Request):
    """Link a new client to the current advocate (create ADVOCACY relationship)."""
    user_id = require_request_user_id(request)
    _require_advocate(user_id)

    async with get_db_session() as db:
        # Verify tenant exists
        tenant = await db.get(User, body.tenant_user_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant user not found")

        # Check if relationship already exists
        existing = (
            await db.execute(
                select(UserRelationship).where(
                    UserRelationship.from_user_id == user_id,
                    UserRelationship.to_user_id == body.tenant_user_id,
                    UserRelationship.relationship_type == RelationshipType.ADVOCACY.value,
                )
            )
        ).scalars().first()
        if existing:
            if existing.is_active:
                raise HTTPException(status_code=409, detail="Advocacy relationship already exists")
            # Reactivate
            existing.is_active = True
            existing.updated_at = utc_now()
            if body.notes:
                existing.context = {"notes": body.notes}
            await db.commit()
            return {"relationship_id": existing.id, "status": "reactivated", "client_id": tenant.id}

        rel = UserRelationship(
            from_user_id=user_id,
            to_user_id=body.tenant_user_id,
            relationship_type=RelationshipType.ADVOCACY.value,
            is_active=True,
            context={"notes": body.notes} if body.notes else None,
            created_by=user_id,
        )
        db.add(rel)
        await db.commit()
        await db.refresh(rel)

        logger.info("Advocate %s linked to tenant %s (rel_id=%s)", user_id, tenant.id, rel.id)
        return {"relationship_id": rel.id, "status": "created", "client_id": tenant.id}


@router.get("/timeline")
async def merged_timeline(request: Request, client_id: str | None = None):
    """Get merged timeline across all clients, or a single client's timeline."""
    user_id = require_request_user_id(request)
    _require_advocate(user_id)

    async with get_db_session() as db:
        if client_id:
            await _check_client_link(db, user_id, client_id)
            events = await list_events_for_user_id(client_id)
        else:
            rels = await _get_clients_for_advocate(db, user_id)
            if not rels:
                return {"events": [], "count": 0}
            client_ids = [r.to_user_id for r in rels]
            events = []
            for cid in client_ids:
                events.extend(await list_events_for_user_id(cid))
        events.sort(key=lambda e: e.created_at or utc_now(), reverse=True)
        events = events[:100]

        return {
            "events": [
                {
                    "id": e.id,
                    "client_id": e.user_id,
                    "title": getattr(e, "title", None) or getattr(e, "description", ""),
                    "description": getattr(e, "description", ""),
                    "severity": getattr(e, "severity", "normal"),
                    "event_date": e.event_date.isoformat() if getattr(e, "event_date", None) else None,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events
            ],
            "count": len(events),
        }


@router.get("/clients/{client_id}/documents")
async def client_documents(client_id: str, request: Request):
    """Get a client's documents for review."""
    user_id = require_request_user_id(request)
    _require_advocate(user_id)

    async with get_db_session() as db:
        rel = await _check_client_link_logged(db, user_id, client_id, "list_documents")
        docs = (
            await db.execute(
                _advocate_visible_doc_stmt(client_id)
                .order_by(Document.uploaded_at.desc())
                .limit(100)
            )
        ).scalars().all()
        await _log_doc_access(db, user_id, client_id, "list_documents", detail=f"count={len(docs)}")

        reviews = (rel.context or {}).get("document_reviews", {})
        return {
            "client_id": client_id,
            "documents": [
                {
                    "id": d.id,
                    "filename": getattr(d, "filename", None) or getattr(d, "name", ""),
                    "doc_type": getattr(d, "doc_type", None) or getattr(d, "document_type", ""),
                    "certified": bool(getattr(d, "certificate_path", None)),
                    "review_status": (reviews.get(d.id) or {}).get("status"),
                    "created_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
                }
                for d in docs
            ],
            "count": len(docs),
        }


@router.get("/clients/{client_id}/documents/{doc_id}/view")
async def view_client_document(
    client_id: str,
    doc_id: str,
    request: Request,
):
    """Stream a client's document to the advocate, read-only.

    The document is served as-is from the tenant's vault storage — the
    advocate can view and annotate via overlays, but the original bytes
    are never writable through this path. Every view is recorded in
    document_access_logs.
    """
    user_id = require_request_user_id(request)
    _require_advocate(user_id)

    async with get_db_session() as db:
        await _check_client_link_logged(db, user_id, client_id, "view_document")
        doc = (
            await db.execute(
                _advocate_visible_doc_stmt(client_id).where(Document.id == doc_id)
            )
        ).scalars().first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        file_path = doc.file_path
        mime_type = doc.mime_type or "application/octet-stream"
        safe_name = (doc.original_filename or "document").replace('"', "").replace("\r", "").replace("\n", "")
        await _log_doc_access(db, user_id, client_id, "view_document", document_id=doc_id)

    storage = await _get_tenant_storage(client_id)

    try:
        data = await storage.download_file(file_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Advocate view doc %s failed: %s", doc_id, e, exc_info=True)
        raise HTTPException(status_code=502, detail="Could not load the document from storage.")

    return Response(
        content=data,
        media_type=mime_type,
        headers={"Content-Disposition": f'inline; filename="{safe_name}"'},
    )


@router.post("/clients/{client_id}/documents/{doc_id}/review")
async def review_document(
    client_id: str,
    doc_id: str,
    body: ReviewRequest,
    request: Request,
):
    """Mark a client's document as reviewed by the advocate."""
    user_id = require_request_user_id(request)
    _require_advocate(user_id)

    if body.status not in ("reviewed", "flagged", "approved"):
        raise HTTPException(status_code=400, detail="status must be: reviewed, flagged, or approved")

    async with get_db_session() as db:
        rel = await _check_client_link_logged(db, user_id, client_id, "review")
        doc = (
            await db.execute(
                _advocate_visible_doc_stmt(client_id).where(Document.id == doc_id)
            )
        ).scalars().first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Store review as context metadata on the relationship
        # (Document model doesn't have a review field; we track via relationship context)
        ctx = dict(rel.context) if rel.context else {}
        reviews = ctx.get("document_reviews", {})
        reviews[doc_id] = {
            "status": body.status,
            "notes": body.notes,
            "reviewed_by": user_id,
            "reviewed_at": utc_now().isoformat(),
        }
        ctx["document_reviews"] = reviews
        rel.context = ctx
        await db.commit()
        await _log_doc_access(db, user_id, client_id, "review", document_id=doc_id, detail=f"status={body.status}")

        logger.info("Advocate %s reviewed doc %s for client %s: %s", user_id, doc_id, client_id, body.status)
        return {"success": True, "doc_id": doc_id, "status": body.status}


# =============================================================================
# Overlay Annotation Endpoints (Phase 4.2 — Document Review with Overlays)
# =============================================================================
# Overlays are stored in the TENANT's cloud storage (since that's where the
# original document lives), but created_by = advocate's user_id, so ownership
# and audit trail are preserved. The tenant sees the advocate's annotations
# when viewing their document.
# =============================================================================


async def _get_tenant_storage(tenant_user_id: str):
    """Get a storage provider instance for a tenant user.

    Uses the tenant's OAuth token (refreshed if needed) and their
    primary provider. Raises HTTPException if token or provider unavailable.
    """
    from app.core.auto_refresh import ensure_valid_token
    from app.core.database import get_session_factory
    from app.services.storage import get_provider

    provider_name = get_provider_from_user_id(tenant_user_id)
    if not provider_name:
        raise HTTPException(
            status_code=400,
            detail="Could not determine storage provider from tenant user_id.",
        )

    token = None
    try:
        factory = get_session_factory()
        async with factory() as db:
            _, token_obj, _ = await ensure_valid_token(tenant_user_id, db)
            token = token_obj.access_token if token_obj else None
    except Exception as e:
        logger.warning("Advocate annotate: token lookup failed for %s: %s", tenant_user_id, e)
        token = None

    if not token:
        raise HTTPException(
            status_code=403,
            detail="Tenant's storage token unavailable. Tenant must re-authenticate.",
        )

    try:
        return get_provider(provider_name, access_token=token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Storage provider error: {e}")


class AnnotateRequest(BaseModel):
    """Request to create an annotation overlay on a client's document."""

    overlay_type: str = Field(
        ...,
        description="Overlay type: NOTE, HIGHLIGHT, FOOTNOTE, or TRACKED_EDIT",
    )
    payload: dict = Field(
        ...,
        description="Type-specific payload (see unified_overlay_models.py for schema)",
    )
    metadata: dict | None = Field(
        default=None,
        description="Optional metadata (source, jurisdiction, reason, etc.)",
    )


@router.post("/clients/{client_id}/documents/{doc_id}/annotate")
async def annotate_document(
    client_id: str,
    doc_id: str,
    body: AnnotateRequest,
    request: Request,
):
    """Create an annotation overlay on a client's document.

    The advocate creates the overlay; it is stored in the tenant's cloud
    storage with created_by = advocate's user_id. The tenant sees the
    annotation when viewing their document.

    Supported overlay_type values:
    - NOTE — general note (payload: {content, note_type, range?})
    - HIGHLIGHT — highlighted text (payload: {range, color, note?})
    - FOOTNOTE — numbered footnote (payload: {number, range, content, citation?})
    - TRACKED_EDIT — suggested edit (payload: {range, original_text, new_text})
    """
    user_id = require_request_user_id(request)
    _require_advocate(user_id)

    allowed_types = ("NOTE", "HIGHLIGHT", "FOOTNOTE", "TRACKED_EDIT")
    if body.overlay_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"overlay_type must be one of {allowed_types}",
        )

    async with get_db_session() as db:
        await _check_client_link_logged(db, user_id, client_id, "annotate")
        doc = (
            await db.execute(
                _advocate_visible_doc_stmt(client_id).where(Document.id == doc_id)
            )
        ).scalars().first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        vault_path = doc.file_path
        document_id = doc.id

    storage = await _get_tenant_storage(client_id)

    try:
        from app.core.overlay_types import OverlayType
        from app.models.unified_overlay_models import CreateOverlayRequest
        from app.services.unified_overlay_manager import UnifiedOverlayManager

        overlay_type_enum = OverlayType[body.overlay_type]
        mgr = UnifiedOverlayManager(storage, user_id)
        resp = await mgr.create_overlay(
            CreateOverlayRequest(
                overlay_type=overlay_type_enum,
                document_id=document_id,
                vault_path=vault_path,
                payload=body.payload,
                metadata=body.metadata or {"source": "advocate_review"},
                ephemeral=False,
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Advocate annotate: create_overlay failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create overlay: {e}")

    if not resp.success:
        raise HTTPException(status_code=500, detail=resp.message)

    logger.info(
        "Advocate %s annotated doc %s for client %s (type=%s, overlay_id=%s)",
        user_id,
        doc_id,
        client_id,
        body.overlay_type,
        resp.overlay_id,
    )
    async with get_db_session() as db:
        await _log_doc_access(
            db, user_id, client_id, "annotate",
            document_id=doc_id,
            detail=f"type={body.overlay_type} overlay={resp.overlay_id}",
        )
    return {
        "success": True,
        "overlay_id": resp.overlay_id,
        "overlay_type": body.overlay_type,
        "document_id": document_id,
    }


@router.get("/clients/{client_id}/documents/{doc_id}/overlays")
async def list_document_overlays(
    client_id: str,
    doc_id: str,
    request: Request,
):
    """List all overlays on a client's document.

    Returns all overlays (by any creator) on the document. The advocate
    can see their own annotations plus any the tenant created.
    """
    user_id = require_request_user_id(request)
    _require_advocate(user_id)

    async with get_db_session() as db:
        await _check_client_link_logged(db, user_id, client_id, "view_overlays")
        doc = (
            await db.execute(
                _advocate_visible_doc_stmt(client_id).where(Document.id == doc_id)
            )
        ).scalars().first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        await _log_doc_access(db, user_id, client_id, "view_overlays", document_id=doc_id)

    storage = await _get_tenant_storage(client_id)

    try:
        from app.services.unified_overlay_manager import UnifiedOverlayManager

        mgr = UnifiedOverlayManager(storage, client_id)
        resp = await mgr.get_overlays(document_id=doc_id, include_ephemeral=False)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Advocate list overlays failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list overlays: {e}")

    overlays = resp.overlays if hasattr(resp, "overlays") else []
    return {
        "document_id": doc_id,
        "overlays": [
            {
                "overlay_id": o.overlay_id,
                "overlay_type": o.overlay_type.value if hasattr(o.overlay_type, "value") else str(o.overlay_type),
                "created_by": o.created_by,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "payload": o.payload,
                "metadata": o.metadata,
                "is_mine": o.created_by == user_id,
            }
            for o in overlays
        ],
        "count": len(overlays),
    }


@router.delete("/clients/{client_id}/overlays/{overlay_id}")
async def delete_annotation(
    client_id: str,
    overlay_id: str,
    request: Request,
):
    """Delete an overlay created by the advocate on a client's document.

    Only the overlay's creator (the advocate) can delete it. The tenant's
    original document is never touched.
    """
    user_id = require_request_user_id(request)
    _require_advocate(user_id)

    async with get_db_session() as db:
        await _check_client_link_logged(db, user_id, client_id, "delete_overlay")

    storage = await _get_tenant_storage(client_id)

    try:
        from app.services.unified_overlay_manager import UnifiedOverlayManager

        mgr = UnifiedOverlayManager(storage, user_id)
        overlay = await mgr.get_overlay(overlay_id)
        if overlay is None:
            raise HTTPException(status_code=404, detail="Overlay not found")
        if overlay.created_by != user_id:
            raise HTTPException(
                status_code=403,
                detail="You can only delete overlays you created.",
            )
        deleted = await mgr.delete_overlay(overlay_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Advocate delete overlay failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete overlay: {e}")

    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete overlay")

    logger.info(
        "Advocate %s deleted overlay %s for client %s",
        user_id,
        overlay_id,
        client_id,
    )
    async with get_db_session() as db:
        await _log_doc_access(db, user_id, client_id, "delete_overlay", detail=f"overlay={overlay_id}")
    return {"success": True, "overlay_id": overlay_id}


# =============================================================================
# Invite Flow Endpoints (Phase 4.2 — Invite Flow UI)
# =============================================================================
# Advocates can't create invite codes (only managers/admins can), but they
# CAN view codes from their organization and share them with tenants.
# The advocate's org is determined via TEAM_MEMBER relationship to their
# manager, and the manager's user_id[:12] is used as org_id.
# =============================================================================


@router.get("/invite-codes")
async def list_org_invite_codes(request: Request):
    """List invite codes from the advocate's organization.

    Finds the advocate's manager via TEAM_MEMBER relationship, then
    returns all codes from that manager's organization. Only active,
    non-expired codes with remaining uses are returned by default.
    """
    user_id = require_request_user_id(request)
    _require_advocate(user_id)

    from app.models.models import InviteCode

    async with get_db_session() as db:
        # Find advocate's manager via TEAM_MEMBER relationship
        team_rel = (
            await db.execute(
                select(UserRelationship).where(
                    UserRelationship.from_user_id == user_id,
                    UserRelationship.relationship_type == RelationshipType.TEAM_MEMBER.value,
                    UserRelationship.is_active.is_(True),
                )
            )
        ).scalars().first()

        if not team_rel:
            return {
                "codes": [],
                "count": 0,
                "message": "No organization linked. Ask your manager to add you to the team.",
            }

        manager_id = team_rel.to_user_id
        org_id = manager_id[:12]

        # Get active, non-expired codes from this org
        codes = (
            await db.execute(
                select(InviteCode).where(
                    InviteCode.organization_id == org_id,
                    InviteCode.is_active.is_(True),
                )
            )
        ).scalars().all()

        # Filter out expired and used-up codes
        now = utc_now()
        available = []
        for c in codes:
            if c.is_expired:
                continue
            if c.expires_at and c.expires_at < now:
                continue
            if c.remaining_uses <= 0:
                continue
            available.append(
                {
                    "code": c.code,
                    "role": c.role,
                    "max_uses": c.max_uses,
                    "uses_count": c.uses_count,
                    "remaining_uses": c.remaining_uses,
                    "expires_at": c.expires_at.isoformat() if c.expires_at else None,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "description": c.description,
                }
            )

        return {
            "codes": available,
            "count": len(available),
            "organization_id": org_id,
        }


# =============================================================================
# Tenant-Side Case Sharing (Phase 4.2 — Case Sharing)
# =============================================================================
# These endpoints are called by TENANTS, not advocates. No advocate role
# check. Any authenticated user can call them to link to an advocate.
# The ADVOCACY relationship is created with from_user_id=advocate,
# to_user_id=tenant, matching the existing intake pattern.
# =============================================================================


class LinkAdvocateRequest(BaseModel):
    """Tenant requests to link to an advocate by entering the advocate's user_id."""

    advocate_user_id: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="The advocate's user_id (shared by the advocate)",
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Optional message from tenant to advocate",
    )


@router.post("/link-request")
async def tenant_link_advocate(body: LinkAdvocateRequest, request: Request):
    """Tenant initiates case sharing with an advocate.

    Creates an ADVOCACY relationship (from=advocate, to=tenant) so the
    advocate can access the tenant's case data. The advocate must already
    have an account with the advocate role.

    This is the tenant-side equivalent of the advocate intake flow.
    """
    user_id = require_request_user_id(request)

    # Verify target user exists and is an advocate
    target_role = get_role_from_user_id(body.advocate_user_id)
    if target_role != UserRole.ADVOCATE:
        raise HTTPException(
            status_code=400,
            detail="The provided user_id is not an advocate. Ask your advocate for their Semptify ID.",
        )

    async with get_db_session() as db:
        # Check if relationship already exists
        existing = (
            await db.execute(
                select(UserRelationship).where(
                    UserRelationship.from_user_id == body.advocate_user_id,
                    UserRelationship.to_user_id == user_id,
                    UserRelationship.relationship_type == RelationshipType.ADVOCACY.value,
                )
            )
        ).scalars().first()
        if existing:
            if existing.is_active:
                return {
                    "success": True,
                    "message": "You are already linked to this advocate.",
                    "already_linked": True,
                }
            # Reactivate
            existing.is_active = True
            existing.context = {"notes": body.notes} if body.notes else existing.context
            existing.created_by = user_id
            await db.commit()
            return {
                "success": True,
                "message": "Relationship reactivated.",
                "reactivated": True,
            }

        # Create new relationship
        rel = UserRelationship(
            from_user_id=body.advocate_user_id,
            to_user_id=user_id,
            relationship_type=RelationshipType.ADVOCACY.value,
            is_active=True,
            context={"notes": body.notes, "initiated_by": "tenant"} if body.notes else {"initiated_by": "tenant"},
            created_by=user_id,
        )
        db.add(rel)
        await db.commit()

    logger.info(
        "Tenant %s linked to advocate %s (tenant-initiated)",
        user_id,
        body.advocate_user_id,
    )
    return {
        "success": True,
        "message": "You are now linked to the advocate. They can see your case.",
    }


@router.get("/my-advocates")
async def list_my_advocates(request: Request):
    """List all advocates linked to the current tenant.

    Returns all active ADVOCACY relationships where the current user is
    the tenant (to_user_id). Tenants can use this to see who has access
    to their case and revoke access if needed.
    """
    user_id = require_request_user_id(request)

    async with get_db_session() as db:
        rels = (
            await db.execute(
                select(UserRelationship).where(
                    UserRelationship.to_user_id == user_id,
                    UserRelationship.relationship_type == RelationshipType.ADVOCACY.value,
                    UserRelationship.is_active.is_(True),
                )
            )
        ).scalars().all()

        return {
            "advocates": [
                {
                    "advocate_user_id": r.from_user_id,
                    "linked_at": r.created_at.isoformat() if r.created_at else None,
                    "initiated_by": (r.context or {}).get("initiated_by", "advocate"),
                    "notes": (r.context or {}).get("notes"),
                }
                for r in rels
            ],
            "count": len(rels),
        }


@router.delete("/my-advocates/{advocate_user_id}")
async def revoke_advocate_access(advocate_user_id: str, request: Request):
    """Tenant revokes an advocate's access to their case.

    Deactivates the ADVOCACY relationship. The advocate can no longer
    see the tenant's data. Can be reactivated later via link-request.
    """
    user_id = require_request_user_id(request)

    async with get_db_session() as db:
        rel = (
            await db.execute(
                select(UserRelationship).where(
                    UserRelationship.from_user_id == advocate_user_id,
                    UserRelationship.to_user_id == user_id,
                    UserRelationship.relationship_type == RelationshipType.ADVOCACY.value,
                    UserRelationship.is_active.is_(True),
                )
            )
        ).scalars().first()
        if not rel:
            raise HTTPException(status_code=404, detail="No active link to this advocate.")

        rel.is_active = False
        await db.commit()

    logger.info(
        "Tenant %s revoked advocate %s access",
        user_id,
        advocate_user_id,
    )
    return {"success": True, "message": "Advocate access revoked."}
