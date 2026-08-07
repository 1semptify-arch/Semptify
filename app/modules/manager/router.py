"""
Manager API Router
==================

Endpoints for manager case assignment, bulk operations, reporting, and permissions.
Complements the 4 existing /api/manager/* endpoints in main.py (dashboard-stats,
cases, staff, activity).

Routes:
- POST /api/manager/cases/{tenant_id}/assign     — assign advocate to tenant case
- POST /api/manager/cases/{tenant_id}/status     — update case status
- POST /api/manager/bulk/export                  — bulk export case data
- GET  /api/manager/reports/cases                — aggregate case report
- GET  /api/manager/reports/staff                — staff productivity report
- POST /api/manager/staff/{user_id}/role         — update staff role
"""

import csv
import io
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.capabilities import require_capability
from app.core.database import get_db_session
from app.core.request_utils import require_request_user_id
from app.core.user_context import UserRole, get_role_from_user_id
from app.core.utc import utc_now
from app.models.models import (
    Document,
    RelationshipType,
    TimelineEvent,
    User,
    UserRelationship,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/manager",
    tags=["Manager"],
    dependencies=[Depends(require_capability("app.modules.manager.router"))],
)


# =============================================================================
# Helpers
# =============================================================================

def _require_manager(user_id: str) -> None:
    """Verify the current user has manager role."""
    role = get_role_from_user_id(user_id)
    if role not in (UserRole.MANAGER, UserRole.ADMIN):
        raise HTTPException(
            status_code=403,
            detail="Only managers can access this endpoint.",
        )


def _org_id_from(user_id: str) -> str:
    """Derive organization id from user_id prefix (SSOT convention)."""
    return user_id[:12]


def _org_user_ids(db, org_id: str) -> list[str]:
    """Return all user_ids in this organization."""
    users = db.query(User).filter(User.id.like(f"{org_id}%")).all()
    return [u.id for u in users]


# =============================================================================
# Request Models
# =============================================================================

class AssignRequest(BaseModel):
    advocate_user_id: str = Field(..., min_length=8, max_length=128)


class CaseStatusRequest(BaseModel):
    status: str = Field(..., description="New case status: active, pending, closed, escalated")


class BulkExportRequest(BaseModel):
    tenant_user_ids: list[str] = Field(..., min_length=1, max_length=100)
    format: str = Field(default="json", description="Export format: json or csv")


class UpdateRoleRequest(BaseModel):
    new_role: str = Field(..., description="New role: advocate or user")


_VALID_CASE_STATUSES = {"active", "pending", "closed", "escalated"}
_VALID_STAFF_ROLES = {"advocate", "user"}


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/cases/{tenant_id}/assign")
async def assign_case(tenant_id: str, body: AssignRequest, request: Request):
    """Assign an advocate to a tenant case (creates ADVOCACY relationship)."""
    user_id = require_request_user_id(request)
    _require_manager(user_id)

    with get_db_session() as db:
        # Verify tenant exists
        tenant = db.query(User).filter_by(id=tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # Verify advocate exists and has advocate role
        advocate = db.query(User).filter_by(id=body.advocate_user_id).first()
        if not advocate:
            raise HTTPException(status_code=404, detail="Advocate not found")

        adv_role = get_role_from_user_id(body.advocate_user_id)
        if adv_role != UserRole.ADVOCATE:
            raise HTTPException(status_code=400, detail="Target user is not an advocate")

        # Check existing relationship
        existing = (
            db.query(UserRelationship)
            .filter(
                UserRelationship.from_user_id == body.advocate_user_id,
                UserRelationship.to_user_id == tenant_id,
                UserRelationship.relationship_type == RelationshipType.ADVOCACY.value,
            )
            .first()
        )
        if existing:
            if existing.is_active:
                raise HTTPException(status_code=409, detail="Advocacy relationship already exists")
            existing.is_active = True
            existing.updated_at = utc_now()
            existing.created_by = user_id
            db.commit()
            return {"relationship_id": existing.id, "status": "reactivated"}

        rel = UserRelationship(
            from_user_id=body.advocate_user_id,
            to_user_id=tenant_id,
            relationship_type=RelationshipType.ADVOCACY.value,
            is_active=True,
            created_by=user_id,
            context={"assigned_by_manager": user_id, "assigned_at": utc_now().isoformat()},
        )
        db.add(rel)
        db.commit()
        db.refresh(rel)

        logger.info("Manager %s assigned advocate %s to tenant %s", user_id, body.advocate_user_id, tenant_id)
        return {"relationship_id": rel.id, "status": "created"}


@router.post("/cases/{tenant_id}/status")
async def update_case_status(tenant_id: str, body: CaseStatusRequest, request: Request):
    """Update a case status. Stored as context on the most recent LEASE or ADVOCACY relationship."""
    user_id = require_request_user_id(request)
    _require_manager(user_id)

    if body.status not in _VALID_CASE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of: {', '.join(sorted(_VALID_CASE_STATUSES))}",
        )

    with get_db_session() as db:
        tenant = db.query(User).filter_by(id=tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # Find any active relationship involving this tenant
        rel = (
            db.query(UserRelationship)
            .filter(
                UserRelationship.to_user_id == tenant_id,
                UserRelationship.is_active.is_(True),
            )
            .order_by(UserRelationship.updated_at.desc())
            .first()
        )
        if not rel:
            raise HTTPException(status_code=404, detail="No active case relationship found for this tenant")

        ctx = dict(rel.context) if rel.context else {}
        ctx["case_status"] = body.status
        ctx["status_updated_by"] = user_id
        ctx["status_updated_at"] = utc_now().isoformat()
        rel.context = ctx
        rel.updated_at = utc_now()
        db.commit()

        logger.info("Manager %s set case %s status to %s", user_id, tenant_id, body.status)
        return {"tenant_id": tenant_id, "case_status": body.status}


@router.post("/bulk/export")
async def bulk_export(body: BulkExportRequest, request: Request):
    """Bulk export case data for a set of tenants."""
    user_id = require_request_user_id(request)
    _require_manager(user_id)

    fmt = body.format.lower()
    if fmt not in ("json", "csv"):
        raise HTTPException(status_code=400, detail="format must be json or csv")

    with get_db_session() as db:
        rows = []
        for tid in body.tenant_user_ids:
            tenant = db.query(User).filter_by(id=tid).first()
            if not tenant:
                rows.append({"tenant_id": tid, "error": "not_found"})
                continue
            doc_count = db.query(Document).filter_by(user_id=tid).count()
            event_count = db.query(TimelineEvent).filter_by(user_id=tid).count()
            rows.append({
                "tenant_id": tid,
                "primary_provider": tenant.primary_provider,
                "default_role": tenant.default_role,
                "intensity_level": tenant.intensity_level,
                "doc_count": doc_count,
                "event_count": event_count,
                "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
                "last_login": tenant.last_login.isoformat() if tenant.last_login else None,
            })

        if fmt == "json":
            return {"format": "json", "exported_by": user_id, "exported_at": utc_now().isoformat(), "cases": rows}

        # CSV
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=[
            "tenant_id", "primary_provider", "default_role", "intensity_level",
            "doc_count", "event_count", "created_at", "last_login", "error",
        ])
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in writer.fieldnames})
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=case_export.csv"},
        )


@router.get("/reports/cases")
async def case_report(request: Request):
    """Aggregate case report for the manager's organization."""
    user_id = require_request_user_id(request)
    _require_manager(user_id)

    org_id = _org_id_from(user_id)
    with get_db_session() as db:
        user_ids = _org_user_ids(db, org_id)
        if not user_ids:
            return {"report": {"total_cases": 0, "by_status": {}, "by_intensity": {}}}

        total_docs = db.query(Document).filter(Document.user_id.in_(user_ids)).count()
        total_events = db.query(TimelineEvent).filter(TimelineEvent.user_id.in_(user_ids)).count()

        # Group by role
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        by_role: dict = {}
        by_intensity: dict = {}
        for u in users:
            r = u.default_role or "user"
            by_role[r] = by_role.get(r, 0) + 1
            lvl = u.intensity_level or "low"
            by_intensity[lvl] = by_intensity.get(lvl, 0) + 1

        # Case statuses (from relationship context)
        rels = (
            db.query(UserRelationship)
            .filter(
                UserRelationship.to_user_id.in_(user_ids),
                UserRelationship.is_active.is_(True),
            )
            .all()
        )
        by_status: dict = {}
        for rel in rels:
            status = (rel.context or {}).get("case_status", "active")
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "report": {
                "organization_id": org_id,
                "total_cases": len(user_ids),
                "total_documents": total_docs,
                "total_events": total_events,
                "by_role": by_role,
                "by_intensity": by_intensity,
                "by_status": by_status,
                "generated_at": utc_now().isoformat(),
            }
        }


@router.get("/reports/staff")
async def staff_report(request: Request):
    """Staff productivity report for the manager's organization."""
    user_id = require_request_user_id(request)
    _require_manager(user_id)

    org_id = _org_id_from(user_id)
    with get_db_session() as db:
        # Staff = users in org who are advocates or managers
        user_ids = _org_user_ids(db, org_id)
        if not user_ids:
            return {"report": {"staff": []}}

        staff_rows = []
        for sid in user_ids:
            role = get_role_from_user_id(sid)
            if role not in (UserRole.ADVOCATE, UserRole.MANAGER):
                continue
            # Cases assigned to this advocate
            cases = (
                db.query(UserRelationship)
                .filter(
                    UserRelationship.from_user_id == sid,
                    UserRelationship.relationship_type == RelationshipType.ADVOCACY.value,
                    UserRelationship.is_active.is_(True),
                )
                .count()
            )
            # Docs reviewed (stored in relationship context)
            rels = (
                db.query(UserRelationship)
                .filter(
                    UserRelationship.from_user_id == sid,
                    UserRelationship.relationship_type == RelationshipType.ADVOCACY.value,
                )
                .all()
            )
            docs_reviewed = 0
            for rel in rels:
                reviews = (rel.context or {}).get("document_reviews", {})
                docs_reviewed += len(reviews)

            staff_rows.append({
                "user_id": sid,
                "role": role.value,
                "active_cases": cases,
                "docs_reviewed": docs_reviewed,
            })

        staff_rows.sort(key=lambda x: x["active_cases"], reverse=True)
        return {"report": {"organization_id": org_id, "staff": staff_rows, "generated_at": utc_now().isoformat()}}


@router.post("/staff/{staff_id}/role")
async def update_staff_role(staff_id: str, body: UpdateRoleRequest, request: Request):
    """Update a staff member's role. Manager can only set advocate or user."""
    user_id = require_request_user_id(request)
    _require_manager(user_id)

    if body.new_role not in _VALID_STAFF_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"new_role must be one of: {', '.join(sorted(_VALID_STAFF_ROLES))}",
        )

    with get_db_session() as db:
        staff = db.query(User).filter_by(id=staff_id).first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff user not found")

        old_role = staff.default_role
        staff.default_role = body.new_role
        staff.updated_at = utc_now()
        db.commit()

        logger.info("Manager %s updated staff %s role: %s -> %s", user_id, staff_id, old_role, body.new_role)
        return {"staff_id": staff_id, "old_role": old_role, "new_role": body.new_role}
