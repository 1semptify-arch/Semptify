"""
Advocate API Router
===================

Endpoints for advocate case management:
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
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.database import get_db_session
from app.core.request_utils import require_request_user_id
from app.core.user_context import get_role_from_user_id, UserRole
from app.core.utc import utc_now
from app.models.models import (
    User,
    UserRelationship,
    RelationshipType,
    Document,
    TimelineEvent,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/advocate", tags=["Advocate"])


# =============================================================================
# Helpers
# =============================================================================

def _require_advocate(user_id: str) -> None:
    """Verify the current user has advocate role."""
    role = get_role_from_user_id(user_id)
    if role not in (UserRole.ADVOCATE, UserRole.ADMIN):
        raise HTTPException(
            status_code=403,
            detail="Only advocates can access this endpoint.",
        )


def _get_clients_for_advocate(db, advocate_id: str):
    """Return all active ADVOCACY relationships for this advocate."""
    return (
        db.query(UserRelationship)
        .filter(
            UserRelationship.from_user_id == advocate_id,
            UserRelationship.relationship_type == RelationshipType.ADVOCACY.value,
            UserRelationship.is_active.is_(True),
        )
        .all()
    )


def _check_client_link(db, advocate_id: str, client_id: str) -> UserRelationship:
    """Verify advocate has access to this client. Returns the relationship."""
    rel = (
        db.query(UserRelationship)
        .filter(
            UserRelationship.from_user_id == advocate_id,
            UserRelationship.to_user_id == client_id,
            UserRelationship.relationship_type == RelationshipType.ADVOCACY.value,
            UserRelationship.is_active.is_(True),
        )
        .first()
    )
    if not rel:
        raise HTTPException(
            status_code=403,
            detail="No active advocacy relationship with this client.",
        )
    return rel


# =============================================================================
# Request Models
# =============================================================================

class IntakeRequest(BaseModel):
    tenant_user_id: str = Field(..., min_length=8, max_length=128, description="Tenant's user_id")
    notes: Optional[str] = Field(default=None, max_length=500, description="Optional intake notes")


class ReviewRequest(BaseModel):
    status: str = Field(default="reviewed", description="Review status: reviewed, flagged, approved")
    notes: Optional[str] = Field(default=None, max_length=500, description="Review notes")


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/clients")
async def list_clients(request: Request):
    """List all clients linked to the current advocate."""
    user_id = require_request_user_id(request)
    _require_advocate(user_id)

    with get_db_session() as db:
        rels = _get_clients_for_advocate(db, user_id)
        clients = []
        for rel in rels:
            tenant = db.query(User).filter_by(id=rel.to_user_id).first()
            if not tenant:
                continue
            doc_count = db.query(Document).filter_by(user_id=tenant.id).count()
            event_count = db.query(TimelineEvent).filter_by(user_id=tenant.id).count()
            clients.append({
                "user_id": tenant.id,
                "primary_provider": tenant.primary_provider,
                "doc_count": doc_count,
                "event_count": event_count,
                "linked_at": rel.created_at.isoformat() if rel.created_at else None,
                "context": rel.context,
            })
        return {"advocate_id": user_id, "clients": clients, "count": len(clients)}


@router.get("/clients/{client_id}")
async def client_detail(client_id: str, request: Request):
    """Get a single client's profile and stats."""
    user_id = require_request_user_id(request)
    _require_advocate(user_id)

    with get_db_session() as db:
        _check_client_link(db, user_id, client_id)
        tenant = db.query(User).filter_by(id=client_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Client not found")

        doc_count = db.query(Document).filter_by(user_id=tenant.id).count()
        event_count = db.query(TimelineEvent).filter_by(user_id=tenant.id).count()
        recent_events = (
            db.query(TimelineEvent)
            .filter_by(user_id=tenant.id)
            .order_by(TimelineEvent.created_at.desc())
            .limit(5)
            .all()
        )

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

    with get_db_session() as db:
        rels = _get_clients_for_advocate(db, user_id)
        if not rels:
            return {"queue": [], "count": 0}

        client_ids = [r.to_user_id for r in rels]
        # Get recent events across all clients
        events = (
            db.query(TimelineEvent)
            .filter(TimelineEvent.user_id.in_(client_ids))
            .order_by(TimelineEvent.created_at.desc())
            .limit(50)
            .all()
        )

        queue = []
        for e in events:
            title = getattr(e, "title", None) or getattr(e, "description", "")
            severity = getattr(e, "severity", "normal")
            queue.append({
                "client_id": e.user_id,
                "event_id": e.id,
                "title": title,
                "severity": severity,
                "event_date": e.event_date.isoformat() if getattr(e, "event_date", None) else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "urgent": severity in ("high", "urgent", "critical"),
            })

        # Sort: urgent first, then by created_at desc
        queue.sort(key=lambda x: (not x["urgent"], x["created_at"] or ""), reverse=False)
        queue.sort(key=lambda x: x["urgent"], reverse=True)

        return {"queue": queue, "count": len(queue)}


@router.post("/intake")
async def new_intake(body: IntakeRequest, request: Request):
    """Link a new client to the current advocate (create ADVOCACY relationship)."""
    user_id = require_request_user_id(request)
    _require_advocate(user_id)

    with get_db_session() as db:
        # Verify tenant exists
        tenant = db.query(User).filter_by(id=body.tenant_user_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant user not found")

        # Check if relationship already exists
        existing = (
            db.query(UserRelationship)
            .filter(
                UserRelationship.from_user_id == user_id,
                UserRelationship.to_user_id == body.tenant_user_id,
                UserRelationship.relationship_type == RelationshipType.ADVOCACY.value,
            )
            .first()
        )
        if existing:
            if existing.is_active:
                raise HTTPException(status_code=409, detail="Advocacy relationship already exists")
            # Reactivate
            existing.is_active = True
            existing.updated_at = utc_now()
            if body.notes:
                existing.context = {"notes": body.notes}
            db.commit()
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
        db.commit()
        db.refresh(rel)

        logger.info("Advocate %s linked to tenant %s (rel_id=%s)", user_id, tenant.id, rel.id)
        return {"relationship_id": rel.id, "status": "created", "client_id": tenant.id}


@router.get("/timeline")
async def merged_timeline(request: Request, client_id: Optional[str] = None):
    """Get merged timeline across all clients, or a single client's timeline."""
    user_id = require_request_user_id(request)
    _require_advocate(user_id)

    with get_db_session() as db:
        if client_id:
            _check_client_link(db, user_id, client_id)
            events = (
                db.query(TimelineEvent)
                .filter_by(user_id=client_id)
                .order_by(TimelineEvent.created_at.desc())
                .limit(100)
                .all()
            )
        else:
            rels = _get_clients_for_advocate(db, user_id)
            if not rels:
                return {"events": [], "count": 0}
            client_ids = [r.to_user_id for r in rels]
            events = (
                db.query(TimelineEvent)
                .filter(TimelineEvent.user_id.in_(client_ids))
                .order_by(TimelineEvent.created_at.desc())
                .limit(100)
                .all()
            )

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

    with get_db_session() as db:
        _check_client_link(db, user_id, client_id)
        docs = (
            db.query(Document)
            .filter_by(user_id=client_id)
            .order_by(Document.created_at.desc())
            .limit(100)
            .all()
        )

        return {
            "client_id": client_id,
            "documents": [
                {
                    "id": d.id,
                    "filename": getattr(d, "filename", None) or getattr(d, "name", ""),
                    "doc_type": getattr(d, "doc_type", None) or getattr(d, "document_type", ""),
                    "certified": getattr(d, "is_certified", False),
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
                for d in docs
            ],
            "count": len(docs),
        }


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

    with get_db_session() as db:
        _check_client_link(db, user_id, client_id)
        doc = db.query(Document).filter_by(id=doc_id, user_id=client_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Store review as context metadata on the relationship
        # (Document model doesn't have a review field; we track via relationship context)
        rel = _check_client_link(db, user_id, client_id)
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
        db.commit()

        logger.info("Advocate %s reviewed doc %s for client %s: %s", user_id, doc_id, client_id, body.status)
        return {"success": True, "doc_id": doc_id, "status": body.status}
