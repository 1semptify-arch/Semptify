"""Case File Review & Evidence Index — API router.

Locked spec (2026-09-27): per-case document categorization + cross-document
evidence index, persisted as EVIDENCE_INDEX overlays in the tenant's own
cloud vault. Original documents are immutable — this module has no endpoint
that writes to a document; the viewer embeds the read-only DC stream.

Unlock model (spec §8, SUPERSEDED 2026-09-28): the module still unlocks on
``legal_share_initialized``, but sharing now happens INSIDE Semptify via the
legal_share module — creating a /r/{token} case-share link writes the
share_marker overlay and grants this module's capability through this same
marker/grant path (legal_share calls mark_share_initialized + grant_capability
here, so the flag stays single-sourced). The POST endpoint below remains the
manual self-mark for tenants who shared a file some other way.

Route layout (mounted at /api/case-review):
  GET  /status                                    — unlocked flag (ungated; it IS the lock check)
  POST /share-initialized                         — set the flag (ungated; it IS the unlock action)
  GET  /cases                                     — incident picker list
  GET  /cases/{case_id}/documents                 — vault docs merged with case tags
  PUT  /cases/{case_id}/documents/{doc_id}/tag    — set category + evidence_type
  DELETE /cases/{case_id}/documents/{doc_id}/tag  — remove a doc from the case index
  GET  /cases/{case_id}/legend                    — color legend entries
  PUT  /cases/{case_id}/legend                    — replace legend entries
  GET  /cases/{case_id}/notes                     — evidence notes (multi-doc links)
  POST /cases/{case_id}/notes                     — create note
  PUT  /cases/{case_id}/notes/{note_id}           — update note
  DELETE /cases/{case_id}/notes/{note_id}         — delete note
  GET  /cases/{case_id}/export                    — paste-ready plain-text index
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.capabilities import get_user_capabilities, grant_capability
from app.core.database import get_db
from app.core.request_utils import get_request_user_id
from app.core.security import StorageUser, yellow_access
from app.modules.case_review import service
from app.services.incident_store import list_incidents

logger = logging.getLogger(__name__)

MODULE_PATH = "app.modules.case_review.router"

router = APIRouter(tags=["Case Review"])


# =============================================================================
# Request models
# =============================================================================


class ShareInitRequest(BaseModel):
    case_id: int | None = None


class TagSetRequest(BaseModel):
    category: str
    evidence_type: str
    name: str | None = None
    vault_path: str | None = None


class LegendEntry(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    color: str = Field(default="#f2d16b", max_length=20)


class LegendSetRequest(BaseModel):
    entries: list[LegendEntry] = Field(default_factory=list, max_length=12)


class NoteLink(BaseModel):
    document_id: str
    vault_path: str | None = None
    name: str | None = None
    location: str | None = None


class NoteCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    links: list[NoteLink] = Field(default_factory=list, max_length=50)
    legend_label: str | None = Field(default=None, max_length=120)


class NoteUpdateRequest(BaseModel):
    text: str | None = Field(default=None, max_length=20000)
    links: list[NoteLink] | None = None
    legend_label: str | None = Field(default=None, max_length=120)


# =============================================================================
# Unlock gate — the share marker is authoritative
# =============================================================================


async def _unlocked(user: StorageUser, db: AsyncSession) -> bool:
    """True when legal_share_initialized fired OR the capability was granted
    (e.g. admin grant, __all__ admin). The marker check is separate from the
    capability row because require_capability fails open for unseeded users —
    the marker is the flag's durable record."""
    effective_id = user.get_effective_user_id()
    try:
        if await service.is_share_initialized(user):
            return True
    except Exception as exc:
        logger.warning("Case review share-marker check failed for %s: %s", effective_id[:8], exc)
    try:
        caps = await get_user_capabilities(effective_id, db)
        return MODULE_PATH in caps or "__all__" in caps
    except Exception as exc:
        logger.warning("Case review capability check failed for %s: %s", effective_id[:8], exc)
        return False


async def _require_unlocked(user: StorageUser = Depends(yellow_access), db: AsyncSession = Depends(get_db)) -> StorageUser:
    if not await _unlocked(user, db):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "legal_share_not_initialized",
                "message": "This tool unlocks once you've shared your case file with an attorney or legal reviewer.",
            },
        )
    return user


async def _case_or_404(user: StorageUser, case_id):
    incident = await service.resolve_case(user, case_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return incident


def _doc_row(doc, tags: dict[str, dict]) -> dict:
    tag = tags.get(doc.vault_id) or {}
    return {
        "id": doc.vault_id,
        "vault_id": doc.vault_id,
        "name": doc.filename or doc.safe_filename,
        "document_type": doc.document_type,
        "uploaded_at": doc.uploaded_at,
        "vault_path": doc.storage_path,
        "category": tag.get("category"),
        "evidence_type": tag.get("evidence_type"),
        "tagged": bool(tag),
    }


# =============================================================================
# Flag routes (ungated — they are the unlock mechanism itself)
# =============================================================================


@router.get("/status")
async def cr_status(user: StorageUser = Depends(yellow_access), db: AsyncSession = Depends(get_db)):
    """Module unlock state for the page. Ungated — a locked tenant needs this
    to render the 'share first' state."""
    return {"unlocked": await _unlocked(user, db)}


@router.post("/share-initialized")
async def cr_share_initialized(
    body: ShareInitRequest,
    user: StorageUser = Depends(yellow_access),
    db: AsyncSession = Depends(get_db),
):
    """Tenant declares: 'I've shared my case file with an attorney/legal
    reviewer.' Writes the share_marker overlay and grants the capability."""
    if body.case_id is not None:
        await _case_or_404(user, body.case_id)
    marker = await service.mark_share_initialized(user, body.case_id)
    await grant_capability(user.get_effective_user_id(), MODULE_PATH, db, source=service.LEGAL_SHARE_INITIALIZED)
    return {"unlocked": True, "marker_id": marker.overlay_id if marker else None}


# =============================================================================
# Case + document routes (locked until legal_share_initialized)
# =============================================================================


@router.get("/cases")
async def cr_cases(user: StorageUser = Depends(_require_unlocked)):
    """Cases (incidents) the tenant can build an index for."""
    incidents = await list_incidents(user)
    return {
        "cases": [
            {
                "incident_id": i.incident_id,
                "title": i.title,
                "status": i.status,
                "incident_type": i.incident_type,
                "updated_at": i.updated_at.isoformat() if i.updated_at else None,
            }
            for i in incidents
        ]
    }


@router.get("/cases/{case_id}/documents")
async def cr_case_documents(case_id: int, user: StorageUser = Depends(_require_unlocked)):
    """All vault documents with their case tag (or null). The left pane groups
    by category; untagged docs are the 'add to index' pool."""
    await _case_or_404(user, case_id)
    tags = await service.get_tags(user, case_id)
    documents: list[dict] = []
    try:
        from app.services.vault_upload_service import get_vault_service

        vault_docs = await get_vault_service().get_user_documents(user.user_id)
        documents = [_doc_row(d, tags) for d in vault_docs]
    except Exception as exc:
        logger.warning("Case review vault list failed for %s: %s", user.user_id[:8], exc)
    return {"case_id": case_id, "documents": documents}


@router.put("/cases/{case_id}/documents/{document_id}/tag")
async def cr_tag_document(case_id: int, document_id: str, body: TagSetRequest, user: StorageUser = Depends(_require_unlocked)):
    await _case_or_404(user, case_id)
    tag = await service.set_tag(
        user, case_id, document_id, body.category, body.evidence_type, name=body.name, vault_path=body.vault_path
    )
    if tag is None:
        raise HTTPException(status_code=400, detail="Invalid category or evidence_type")
    return {"document_id": document_id, **tag}


@router.delete("/cases/{case_id}/documents/{document_id}/tag")
async def cr_untag_document(case_id: int, document_id: str, user: StorageUser = Depends(_require_unlocked)):
    await _case_or_404(user, case_id)
    if not await service.remove_tag(user, case_id, document_id):
        raise HTTPException(status_code=404, detail="Document not tagged in this case")
    return {"removed": True}


@router.get("/cases/{case_id}/legend")
async def cr_get_legend(case_id: int, user: StorageUser = Depends(_require_unlocked)):
    await _case_or_404(user, case_id)
    return {"case_id": case_id, "entries": await service.get_legend(user, case_id)}


@router.put("/cases/{case_id}/legend")
async def cr_set_legend(case_id: int, body: LegendSetRequest, user: StorageUser = Depends(_require_unlocked)):
    await _case_or_404(user, case_id)
    entries = await service.set_legend(user, case_id, [e.model_dump() for e in body.entries])
    return {"case_id": case_id, "entries": entries}


@router.get("/cases/{case_id}/notes")
async def cr_list_notes(case_id: int, user: StorageUser = Depends(_require_unlocked)):
    await _case_or_404(user, case_id)
    return {"case_id": case_id, "notes": await service.list_notes(user, case_id)}


@router.post("/cases/{case_id}/notes", status_code=201)
async def cr_create_note(case_id: int, body: NoteCreateRequest, user: StorageUser = Depends(_require_unlocked)):
    await _case_or_404(user, case_id)
    note = await service.create_note(
        user, case_id, body.text, links=[l.model_dump() for l in body.links], legend_label=body.legend_label
    )
    if note is None:
        raise HTTPException(status_code=502, detail="Could not save note to vault storage")
    return note


@router.put("/cases/{case_id}/notes/{note_id}")
async def cr_update_note(case_id: int, note_id: str, body: NoteUpdateRequest, user: StorageUser = Depends(_require_unlocked)):
    await _case_or_404(user, case_id)
    note = await service.update_note(
        user,
        case_id,
        note_id,
        text=body.text,
        links=[l.model_dump() for l in body.links] if body.links is not None else None,
        legend_label=body.legend_label,
    )
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.delete("/cases/{case_id}/notes/{note_id}")
async def cr_delete_note(case_id: int, note_id: str, user: StorageUser = Depends(_require_unlocked)):
    await _case_or_404(user, case_id)
    if not await service.delete_note(user, case_id, note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"deleted": True}


@router.get("/cases/{case_id}/export", response_class=PlainTextResponse)
async def cr_export(case_id: int, user: StorageUser = Depends(_require_unlocked)):
    """Paste-ready plain-text evidence index — the attorney-meeting artifact."""
    incident = await _case_or_404(user, case_id)
    index = await service.build_index(user, case_id)
    doc_names: dict[str, str] = {}
    try:
        from app.services.vault_upload_service import get_vault_service

        for d in await get_vault_service().get_user_documents(user.user_id):
            doc_names[d.vault_id] = d.filename or d.safe_filename
    except Exception as exc:
        logger.warning("Case review export doc-name resolution failed: %s", exc)
    return PlainTextResponse(
        service.render_index_text(incident.title or f"Case {case_id}", index, doc_names),
        media_type="text/plain; charset=utf-8",
    )


# =============================================================================
# Page (HTML) — same pattern as /api/delivery/inbox/page
# =============================================================================


@router.get("/page", response_class=HTMLResponse)
async def case_review_page(request: Request):
    """Serve the Case Review page (3-pane: docs → viewer → evidence index)."""
    user_id = get_request_user_id(request, fallback="")
    if not user_id:
        from app.core.navigation import navigation
        from app.core.ssot_guard import ssot_redirect

        providers_stage = navigation.get_stage("providers")
        providers_path = providers_stage.path if providers_stage else "/storage/providers"
        return ssot_redirect(providers_path, context="case_review_page unauthenticated")
    from app.main import templates

    return templates.TemplateResponse(request, "pages/case_review.html")
