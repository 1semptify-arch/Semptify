"""Legal Share — API + page router.

Supersedes Case Review spec §8 (sharing outside Semptify): the tenant grants
an outside reviewer an expiring, revocable token into a selected slice of
their case file. Reviewers have no Semptify identity — the token is the
credential, resolution is owner-scoped (``{user_id}:{token}``), and all
share/thread state persists as overlays in the tenant's own vault.

Route layout:
  Mounted at /api/legal-share (manifest prefix):
    GET  /cases                                            — case picker for the share flow
    GET  /cases/{case_id}/items                            — shareable items (docs/notes/deadlines)
    POST /shares                                           — create a share (sets legal_share_initialized)
    GET  /shares                                           — tenant's shares with status + unread counts
    GET  /shares/{share_id}/threads                        — all threads on a share (marks tenant-read)
    POST /shares/{share_id}/threads/{thread_id}/reply      — tenant answer
    POST /shares/{share_id}/revoke                         — revoke
    GET  /questions                                        — unread reviewer questions across shares
    GET  /r/{token}                                        — reviewer bundle (token-gated, anonymous)
    GET  /r/{token}/document/{vault_id}                    — shared doc metadata (scope-enforced)
    GET  /r/{token}/document/{vault_id}/content            — shared doc bytes (scope-enforced)
    GET  /r/{token}/threads                                — this share's threads (marks reviewer-read)
    POST /r/{token}/questions                              — reviewer asks a question on a document
    POST /r/{token}/threads/{thread_id}/messages           — reviewer follow-up on a thread
  Mounted at root (pages_router, no prefix):
    GET  /legal-share                                      — tenant share-management page
    GET  /r/{token}                                        — anonymous reviewer page

  Gated release + custody (matrix G9), mounted at /api/legal-share:
    GET  /release/documents                                — tenant's releasable documents
    GET  /release/documents/{doc_id}/integrity             — intake vs recomputed hash + releases
    POST /release/documents/{doc_id}/release               — gated release → NEW artifact
    GET  /release/documents/{doc_id}/releases              — release records for a document
    GET  /release/documents/{doc_id}/releases/{rid}/download — fetch a released bundle
    GET  /release/documents/{doc_id}/custody-log           — chronological custody (downloadable)
"""

from __future__ import annotations

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.capabilities import grant_capability
from app.core.database import get_db
from app.core.event_bus import EventType, event_bus
from app.core.request_utils import get_request_user_id
from app.core.security import StorageUser, get_current_user, get_rate_limiter, yellow_access
from app.core.user_context import UserContext, get_role_from_user_id
from app.core.utc import utc_now
from app.modules.case_review import service as case_review_service
from app.modules.legal_share import release_service, service
from app.services.incident_store import list_incidents

logger = logging.getLogger(__name__)

MODULE_PATH = "app.modules.legal_share.router"
CASE_REVIEW_MODULE_PATH = "app.modules.case_review.router"

router = APIRouter(tags=["Legal Share"])
pages_router = APIRouter(tags=["Legal Share Pages"])

EXPIRY_CHOICES_DAYS = (7, 30, 90)


# =============================================================================
# Request models
# =============================================================================


class ShareCreateRequest(BaseModel):
    case_id: int
    reviewer_label: str = Field(min_length=1, max_length=120)
    reviewer_contact: str | None = Field(default=None, max_length=200)
    tenant_message: str | None = Field(default=None, max_length=2000)
    document_ids: list[str] = Field(default_factory=list, max_length=500)
    include_notes: bool = True
    deadline_ids: list[str] = Field(default_factory=list, max_length=200)
    include_summary: bool = True
    expires_days: int = 30


class QuestionRequest(BaseModel):
    document_id: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)
    subject: str | None = Field(default=None, max_length=200)


class MessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


# =============================================================================
# Token gate — reviewer side. The token is the entire credential: it resolves
# the owner vault, the share record, and its lifecycle state. No cookie, no
# account, no Semptify identity for the reviewer.
# =============================================================================


async def _gate(request: Request) -> tuple:
    """Resolve path token → (share view, owner context). Raises for inactive.

    Failed-token lookups are throttled per source IP: the token lives in the
    URL path, so path-keyed limits could never throttle guessing. Successful
    resolutions are not counted.
    """
    token = request.path_params.get("token", "")
    resolved = await service.resolve_share_with_owner(token)
    err = None
    if not resolved:
        err = (404, "share_not_found")
    else:
        share, owner = resolved
        if share.status == service.STATUS_REVOKED:
            err = (410, "share_revoked")
        elif share.status == service.STATUS_EXPIRED:
            err = (410, "share_expired")
    if err is not None:
        ip = request.client.host if request.client else "unknown"
        allowed, retry_after = get_rate_limiter().check(f"share_guess:{ip}", 60, 30)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail={"error": "rate_limited"},
                headers={"Retry-After": str(retry_after)},
            )
        raise HTTPException(status_code=err[0], detail={"error": err[1]})
    return share, owner


def _share_json(share, unread: int = 0) -> dict:
    return {
        "share_id": share.id,
        "case_id": share.case_id,
        "case_title": share.case_title,
        "reviewer_label": share.reviewer_label,
        "reviewer_contact": share.reviewer_contact,
        "tenant_message": share.tenant_message,
        "documents": share.documents,
        "include_notes": share.include_notes,
        "include_summary": share.include_summary,
        "deadlines": share.deadlines,
        "share_url": f"/r/{share.share_token}",
        "status": share.status,
        "expires_at": share.expires_at.isoformat() if share.expires_at else None,
        "revoked_at": share.revoked_at.isoformat() if share.revoked_at else None,
        "accessed_at": share.accessed_at.isoformat() if share.accessed_at else None,
        "access_count": share.access_count,
        "created_at": share.created_at.isoformat() if share.created_at else None,
        "unread_questions": unread,
    }


# =============================================================================
# Tenant routes
# =============================================================================


@router.get("/cases")
async def ls_cases(user: StorageUser = Depends(yellow_access)):
    """Case picker — the tenant's INCIDENT records (same source as Case Review)."""
    incidents = await list_incidents(user)
    return {
        "cases": [
            {
                "incident_id": i.incident_id,
                "title": i.title,
                "status": i.status,
                "incident_type": i.incident_type,
            }
            for i in incidents
        ]
    }


@router.get("/cases/{case_id}/items")
async def ls_case_items(case_id: int, user: StorageUser = Depends(yellow_access)):
    """Shareable material for a case: vault documents merged with their case
    tags (default-checked when category is filed material — foundational,
    discovery, motion, evidence — off for misc/untagged drafts), evidence
    notes, and the tenant's deadlines (explicit opt-in)."""
    incident = await case_review_service.resolve_case(user, case_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Case not found")

    tags = await case_review_service.get_tags(user, case_id)
    documents: list[dict] = []
    try:
        from app.services.vault_upload_service import get_vault_service

        for d in await get_vault_service().get_user_documents(user.user_id):
            tag = tags.get(d.vault_id) or {}
            documents.append(
                {
                    "id": d.vault_id,
                    "name": d.filename or d.safe_filename,
                    "document_type": d.document_type,
                    "uploaded_at": d.uploaded_at,
                    "vault_path": d.storage_path,
                    "category": tag.get("category"),
                    "evidence_type": tag.get("evidence_type"),
                    "suggested": tag.get("category") in ("foundational", "discovery", "motion", "evidence"),
                }
            )
    except Exception as exc:
        logger.warning("Legal-share vault list failed for %s: %s", user.user_id[:8], exc)

    notes: list[dict] = []
    try:
        notes = await case_review_service.list_notes(user, case_id)
    except Exception as exc:
        logger.warning("Legal-share notes list failed for %s: %s", user.user_id[:8], exc)

    deadlines: list[dict] = []
    try:
        from app.modules.calendar.service import list_events

        events, _total = await list_events(user, limit=500)
        deadlines = [
            {
                "id": e.payload.get("id"),
                "title": e.payload.get("title"),
                "start_datetime": e.payload.get("start_datetime"),
                "event_type": e.payload.get("event_type"),
                "is_critical": e.payload.get("is_critical"),
            }
            for e in events
        ]
    except Exception as exc:
        logger.warning("Legal-share deadline list failed for %s: %s", user.user_id[:8], exc)

    return {
        "case_id": case_id,
        "case_title": incident.title,
        "documents": documents,
        "notes": [{"id": n["id"], "text": n["text"], "document_ids": n["document_ids"]} for n in notes],
        "deadlines": deadlines,
    }


@router.post("/shares", status_code=201)
async def ls_create_share(
    body: ShareCreateRequest,
    user: StorageUser = Depends(yellow_access),
    db: AsyncSession = Depends(get_db),
):
    """Create a CASE_SHARE grant. Also sets the existing legal_share_initialized
    flag via the Case Review share-marker + capability grant (single source)."""
    if body.expires_days not in EXPIRY_CHOICES_DAYS:
        raise HTTPException(status_code=400, detail={"error": "invalid_expiry", "allowed": list(EXPIRY_CHOICES_DAYS)})
    incident = await case_review_service.resolve_case(user, body.case_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Case not found")

    doc_ids = [str(d).strip() for d in body.document_ids if str(d).strip()]
    if not doc_ids:
        raise HTTPException(status_code=400, detail="At least one document must be shared")

    # Snapshot names + verify the documents exist in the tenant's vault.
    docs: list[dict] = []
    try:
        from app.services.vault_upload_service import get_vault_service

        vault_service = get_vault_service()
        for vid in doc_ids:
            doc = await vault_service.get_document(vid)
            if doc is None or doc.user_id != user.user_id:
                # G5.8 — never echo vault ids or paths in error text, even to
                # the owner. One generic message covers not-found + not-yours.
                raise HTTPException(
                    status_code=404,
                    detail={"error": "document_not_found",
                            "message": "One of the selected documents could not be found in your vault."},
                )
            docs.append({"id": vid, "name": doc.filename or doc.safe_filename})
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Legal-share doc lookup failed for %s: %s", user.user_id[:8], exc)
        raise HTTPException(status_code=503, detail="Document vault unavailable") from exc

    deadlines: list[dict] = []
    if body.deadline_ids:
        try:
            from app.modules.calendar.service import get_event

            for eid in body.deadline_ids:
                event = await get_event(user, eid)
                if event is not None:
                    deadlines.append(
                        {
                            "id": eid,
                            "title": event.payload.get("title"),
                            "start_datetime": event.payload.get("start_datetime"),
                        }
                    )
        except Exception as exc:
            logger.warning("Legal-share deadline lookup failed for %s: %s", user.user_id[:8], exc)

    share = await service.create_share(
        user,
        case_id=body.case_id,
        case_title=incident.title,
        reviewer_label=body.reviewer_label,
        reviewer_contact=body.reviewer_contact,
        tenant_message=body.tenant_message,
        documents=docs,
        include_notes=body.include_notes,
        deadlines=deadlines,
        include_summary=body.include_summary,
        expires_at=utc_now() + timedelta(days=body.expires_days),
    )
    if share is None:
        raise HTTPException(status_code=502, detail="Could not save the share to vault storage")

    # Set the capability flag through the existing Case Review path — the
    # share_marker overlay + capability grant stay single-sourced there.
    try:
        await case_review_service.mark_share_initialized(user, body.case_id)
        await grant_capability(
            user.get_effective_user_id(),
            CASE_REVIEW_MODULE_PATH,
            db,
            source=case_review_service.LEGAL_SHARE_INITIALIZED,
        )
    except Exception as exc:
        logger.warning("legal_share_initialized flag failed for %s: %s", user.user_id[:8], exc)

    logger.info("Legal share: created share_id=%s owner=%s case=%s", share.id, user.user_id, body.case_id)
    event_bus.publish_sync(
        EventType.SHARE_LINK_SENT,
        {
            "user_id": user.user_id,
            "case_id": body.case_id,
            "reviewer_label": share.reviewer_label,
            "narrator": {"module": "app.modules.legal_share", "slot": 0},
        },
    )
    return {"ok": True, "share": _share_json(share)}


@router.get("/shares")
async def ls_list_shares(user: StorageUser = Depends(yellow_access)):
    shares = await service.list_shares(user)
    out = []
    for share in shares:
        unread = await service.unread_count_for_share(user, share)
        out.append(_share_json(share, unread=unread))
    return {"shares": out}


@router.get("/shares/{share_id}/threads")
async def ls_share_threads(share_id: str, user: StorageUser = Depends(yellow_access)):
    """All threads on a share. Reading the panel marks them tenant-read."""
    share = await service.get_share(user, share_id)
    if share is None:
        raise HTTPException(status_code=404, detail="Share not found")
    threads = await service.list_threads_for_share(user, share)
    await service.mark_threads_read(user, share.case_id, "tenant", share_id=share.id)
    return {"share_id": share_id, "threads": threads}


@router.post("/shares/{share_id}/threads/{thread_id}/reply")
async def ls_reply(share_id: str, thread_id: str, body: MessageRequest, user: StorageUser = Depends(yellow_access)):
    """Tenant answers a reviewer question. Text is stored verbatim — the
    tenant's own words; Semptify never drafts legal content."""
    share = await service.get_share(user, share_id)
    if share is None:
        raise HTTPException(status_code=404, detail="Share not found")
    threads = {t["thread_id"] for t in await service.list_threads_for_share(user, share)}
    if thread_id not in threads:
        raise HTTPException(status_code=404, detail="Thread not found")
    thread = await service.post_message(user, share.case_id, thread_id, side="tenant", body=body.body)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    event_bus.publish_sync(
        EventType.REVIEW_ANSWER_POSTED,
        {"user_id": user.user_id, "share_id": share_id, "thread_id": thread_id},
    )
    return thread


@router.post("/shares/{share_id}/revoke")
async def ls_revoke(share_id: str, user: StorageUser = Depends(yellow_access)):
    share = await service.revoke_share(user, share_id)
    if share is None:
        raise HTTPException(status_code=404, detail="Share not found")
    logger.info("Legal share: revoked share_id=%s owner=%s", share_id, user.user_id)
    return {"ok": True, "share": _share_json(share)}


@router.get("/questions")
async def ls_unread_questions(user: StorageUser = Depends(yellow_access)):
    """Unread reviewer questions across all active shares (tenant panel)."""
    return {"questions": await service.list_unread_threads(user)}


# =============================================================================
# Reviewer routes — token-gated, anonymous. /api/legal-share/r/ is a public
# prefix in storage_middleware; the token gate (_gate) is the only credential.
# =============================================================================


def _thread_public(t: dict) -> dict:
    """Thread shape exposed to the reviewer — no internal flags beyond status."""
    return {
        "thread_id": t["thread_id"],
        "document_id": t["document_id"],
        "document_name": t["document_name"],
        "subject": t["subject"],
        "status": t["status"],
        "messages": t["messages"],
        "created_at": t["created_at"],
        "answered_at": t["answered_at"],
    }


@router.get("/r/{token}")
async def rs_bundle(token: str, request: Request):
    """Reviewer bundle: share metadata + shared case slice + threads."""
    share, owner = await _gate(request)

    documents = share.documents
    notes: list[dict] = []
    if share.include_notes:
        try:
            allowed = service.shared_document_ids(share)
            notes = [
                {"id": n["id"], "text": n["text"], "document_ids": n["document_ids"]}
                for n in await case_review_service.list_notes(owner, share.case_id)
                if not n["document_ids"] or any(d in allowed for d in n["document_ids"])
            ]
        except Exception as exc:
            logger.warning("Reviewer notes list failed for share %s: %s", share.id, exc)

    summary = None
    if share.include_summary:
        try:
            incident = await case_review_service.resolve_case(owner, share.case_id)
            if incident is not None:
                summary = {
                    "title": incident.title,
                    "status": incident.status,
                    "incident_type": incident.incident_type,
                }
        except Exception as exc:
            logger.warning("Reviewer summary lookup failed for share %s: %s", share.id, exc)

    threads = await service.list_threads_for_share(owner, share)
    await service.record_share_access(token)
    return {
        "status": share.status,
        "reviewer_label": share.reviewer_label,
        "message": share.tenant_message,
        "expires_at": share.expires_at.isoformat() if share.expires_at else None,
        "summary": summary,
        "documents": documents,
        "notes": notes,
        "deadlines": share.deadlines,
        "threads": [_thread_public(t) for t in threads],
    }


@router.get("/r/{token}/threads")
async def rs_threads(token: str, request: Request):
    """This share's threads; loading marks them read by the reviewer."""
    share, owner = await _gate(request)
    threads = await service.list_threads_for_share(owner, share)
    await service.mark_threads_read(owner, share.case_id, "reviewer", share_id=share.id)
    return {"threads": [_thread_public(t) for t in threads]}


@router.get("/r/{token}/document/{vault_id}")
async def rs_document_meta(token: str, vault_id: str, request: Request):
    share, _owner = await _gate(request)
    if vault_id not in service.shared_document_ids(share):
        raise HTTPException(status_code=403, detail={"error": "document_not_shared"})
    try:
        from app.services.vault_upload_service import get_vault_service

        doc = await get_vault_service().get_document(vault_id)
    except Exception as exc:
        logger.warning("Reviewer doc meta lookup failed: %s", exc)
        doc = None
    if doc is None:
        raise HTTPException(status_code=404, detail={"error": "document_not_found"})
    return {
        "vault_id": doc.vault_id,
        "name": doc.filename or doc.safe_filename,
        "mime_type": doc.mime_type,
        "file_size": doc.file_size,
        "uploaded_at": doc.uploaded_at,
        "content_url": f"/api/legal-share/r/{token}/document/{vault_id}/content",
        "download_url": f"/api/legal-share/r/{token}/document/{vault_id}/content?download=1",
    }


@router.get("/r/{token}/document/{vault_id}/content")
async def rs_document_content(token: str, vault_id: str, request: Request):
    """Read-only stream of a shared document — same path as document shares."""
    share, _owner = await _gate(request)
    if vault_id not in service.shared_document_ids(share):
        raise HTTPException(status_code=403, detail={"error": "document_not_shared"})

    from app.services.shared_document_stream import stream_vault_document

    return await stream_vault_document(vault_id, download=bool(request.query_params.get("download")))


@router.post("/r/{token}/questions", status_code=201)
async def rs_post_question(token: str, body: QuestionRequest, request: Request):
    """Reviewer asks a question tied to a shared document. Stored verbatim —
    the reviewer's own words — as a tenant-owned overlay."""
    share, owner = await _gate(request)
    thread = await service.post_question(
        owner, share, document_id=body.document_id, body=body.body, subject=body.subject
    )
    if thread is None:
        raise HTTPException(status_code=403, detail={"error": "document_not_shared"})
    event_bus.publish_sync(
        EventType.REVIEW_QUESTION_POSTED,
        {
            "user_id": owner.user_id,
            "share_id": share.id,
            "thread_id": thread["thread_id"],
            "narrator": {"module": "app.modules.legal_share", "slot": 1},
        },
    )
    return _thread_public(thread)


@router.post("/r/{token}/threads/{thread_id}/messages", status_code=201)
async def rs_followup(token: str, thread_id: str, body: MessageRequest, request: Request):
    """Reviewer follow-up on an existing thread (their side only)."""
    share, owner = await _gate(request)
    threads = {t["thread_id"]: t for t in await service.list_threads_for_share(owner, share)}
    existing = threads.get(thread_id)
    if existing is None:
        raise HTTPException(status_code=404, detail={"error": "thread_not_found"})
    thread = await service.post_message(owner, share.case_id, thread_id, side="reviewer", body=body.body)
    if thread is None:
        raise HTTPException(status_code=404, detail={"error": "thread_not_found"})
    event_bus.publish_sync(
        EventType.REVIEW_QUESTION_POSTED,
        {"user_id": owner.user_id, "share_id": share.id, "thread_id": thread_id},
    )
    return _thread_public(thread)


# =============================================================================
# Gated release + custody (matrix G9.1–G9.6)
# =============================================================================
# These endpoints use get_current_user (not yellow_access) so the deny path is
# reachable and auditable: a linked advocate's release attempt gets an explicit
# logged 403 — never a silent failure — while anyone without a relationship
# gets the same 404 as a nonexistent document.
# =============================================================================


def _release_auth(user: UserContext | None) -> UserContext:
    if user is None:
        raise HTTPException(status_code=401, detail={"error": "not_signed_in"})
    return user


async def _deny_log(db: AsyncSession, actor_id: str, tenant_id: str, doc_id: str, detail: str) -> None:
    """Append-only audit row for a denied release attempt (G9.4)."""
    from app.models.models import DocumentAccessLog

    role = get_role_from_user_id(actor_id)
    db.add(
        DocumentAccessLog(
            actor_user_id=actor_id,
            actor_role=role.value if role else None,
            tenant_user_id=tenant_id,
            document_id=doc_id,
            action="release_denied",
            outcome="denied",
            detail=detail[:500],
        )
    )
    await db.commit()


async def _resolve_for_owner(user: UserContext, doc_id: str, db: AsyncSession):
    """Resolve a document for read-only surfaces. Owner-only — non-owners get
    the same 404 as unknown ids so the surface leaks nothing."""
    ref = await release_service.resolve_document(user, doc_id, db)
    if ref is None or ref.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail={"error": "document_not_found"})
    return ref


async def _resolve_for_release(user: UserContext, doc_id: str, db: AsyncSession):
    """Ownership gate for the gated release. A linked advocate gets an
    explicit, logged denial (the release is the owner's act — never silent);
    anyone else gets the plain 404."""
    from sqlalchemy import select

    from app.models.models import RelationshipType, UserRelationship

    ref = await release_service.resolve_document(user, doc_id, db)
    if ref is None:
        raise HTTPException(status_code=404, detail={"error": "document_not_found"})
    if ref.owner_user_id == user.user_id:
        return ref

    result = await db.execute(
        select(UserRelationship).where(
            UserRelationship.from_user_id == user.user_id,
            UserRelationship.to_user_id == ref.owner_user_id,
            UserRelationship.relationship_type == RelationshipType.ADVOCACY.value,
            UserRelationship.is_active.is_(True),
        )
    )
    if result.scalars().first() is not None:
        await _deny_log(
            db,
            user.user_id,
            ref.owner_user_id,
            ref.canonical_id,
            "Only the document owner can release a copy.",
        )
        logger.info("Release denied for advocate %s on doc %s (owner %s)", user.user_id, ref.canonical_id, ref.owner_user_id)
        raise HTTPException(
            status_code=403,
            detail={"error": "release_denied", "message": "Only the document owner can release a copy."},
        )
    raise HTTPException(status_code=404, detail={"error": "document_not_found"})


@router.get("/release/documents")
async def ls_release_documents(
    user: UserContext | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tenant's releasable documents — the release picker's list."""
    user = _release_auth(user)
    docs = await release_service.list_owner_documents(user, db)
    return {
        "documents": [
            {
                "id": d.canonical_id,
                "name": d.filename,
                "sha256_hash": d.sha256_recorded,
                "mime_type": d.mime_type,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
            }
            for d in docs
        ]
    }


@router.get("/release/documents/{doc_id}/integrity")
async def ls_release_integrity(
    doc_id: str,
    user: UserContext | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Hash lifecycle for one document: intake hash, live recomputed hash,
    every release (artifact hash + timestamp + certificate traveling
    together), and the custody log — G9.5 + G9.6 in one honest surface."""
    user = _release_auth(user)
    ref = await _resolve_for_owner(user, doc_id, db)
    return await release_service.integrity_status(user, ref, db)


@router.get("/release/documents/{doc_id}/custody-log")
async def ls_release_custody_log(
    doc_id: str,
    download: bool = False,
    user: UserContext | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Chronological per-document custody log — intake, cross-party views,
    annotates, shares, releases, denied attempts. ``?download=1`` returns it
    as a JSON attachment for handing to a reviewer or court."""
    user = _release_auth(user)
    ref = await _resolve_for_owner(user, doc_id, db)
    events = await release_service.build_custody_log(user, ref, db)
    body = {
        "document_id": ref.canonical_id,
        "filename": ref.filename,
        "sha256": ref.sha256_recorded,
        "generated_at": utc_now().isoformat(),
        "events": events,
    }
    if download:
        import json

        return Response(
            content=json.dumps(body, indent=2, default=str),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="custody-log-{ref.canonical_id}.json"'
            },
        )
    return body


@router.post("/release/documents/{doc_id}/release")
async def ls_release_create(
    doc_id: str,
    user: UserContext | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """The gated release — the ONE way marked-up state becomes a concrete
    artifact. Produces a NEW bundle under Vault/releases/: original bytes
    (untouched), certificate (hash + timestamp + signature), legend, overlay
    snapshot, custody log. The original file is never written."""
    user = _release_auth(user)
    ref = await _resolve_for_release(user, doc_id, db)
    if not user.access_token or user.access_token == "no-token":
        raise HTTPException(
            status_code=503,
            detail={"error": "storage_unavailable", "message": "Your storage connection needs reconnecting before a release can be made."},
        )
    try:
        record = await release_service.release_document(user, ref, db)
    except RuntimeError as exc:
        if str(exc).startswith("document_bytes_unavailable"):
            raise HTTPException(
                status_code=502,
                detail={"error": "document_bytes_unavailable", "message": "The file couldn't be read just now — nothing was released."},
            ) from exc
        logger.error("Release failed for doc %s: %s", ref.canonical_id, exc)
        raise HTTPException(status_code=500, detail={"error": "release_failed"}) from exc
    return {"release": record}


@router.get("/release/documents/{doc_id}/releases")
async def ls_release_list(
    doc_id: str,
    user: UserContext | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Every release of this document — hash, timestamp, and certificate
    travel together in each record."""
    user = _release_auth(user)
    ref = await _resolve_for_owner(user, doc_id, db)
    return {"releases": await release_service.list_releases(user, ref)}


@router.get("/release/documents/{doc_id}/releases/{release_id}/download")
async def ls_release_download(
    doc_id: str,
    release_id: str,
    user: UserContext | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a released bundle (the artifact itself — a new file, never the
    original)."""
    user = _release_auth(user)
    ref = await _resolve_for_owner(user, doc_id, db)
    found = await release_service.fetch_release_artifact(user, ref, release_id)
    if found is None:
        raise HTTPException(status_code=404, detail={"error": "release_not_found"})
    data, filename = found
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# =============================================================================
# Pages — /legal-share (tenant), /r/{token} (anonymous reviewer)
# =============================================================================


@pages_router.get("/legal-share", response_class=HTMLResponse)
async def legal_share_page(request: Request):
    """Tenant share-management page. Cookie-gated like other app pages."""
    user_id = get_request_user_id(request, fallback="")
    if not user_id:
        from app.core.navigation import navigation
        from app.core.ssot_guard import ssot_redirect

        providers_stage = navigation.get_stage("providers")
        providers_path = providers_stage.path if providers_stage else "/storage/providers"
        return ssot_redirect(providers_path, context="legal_share_page unauthenticated")
    from app.main import templates

    return templates.TemplateResponse(request, "pages/legal_share.html")


@pages_router.get("/r/{token}", response_class=HTMLResponse)
async def reviewer_page(token: str, request: Request):
    """Anonymous reviewer page. Never dead-ends: expired/revoked/unknown tokens
    render a calm 'not available' page rather than an error."""
    share = await service.resolve_share(token)
    from app.main import templates

    if share is None or share.status != service.STATUS_ACTIVE:
        reason = "unavailable"
        if share is not None:
            reason = "revoked" if share.status == service.STATUS_REVOKED else "expired"
        return templates.TemplateResponse(
            request,
            "pages/reviewer_unavailable.html",
            {"reason": reason},
            status_code=200,
        )
    return templates.TemplateResponse(request, "pages/reviewer_share.html", {"token": token})
