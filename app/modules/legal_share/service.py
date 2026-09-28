"""Legal Share service — CASE_SHARE + REVIEW_THREAD overlays in the tenant's vault.

Supersedes Case Review spec §8 (sharing outside Semptify): a tenant grants an
outside attorney/advocate a revocable, expiring link into a selected slice of
their case file. The reviewer has no Semptify identity — the owner-scoped
token is the entire credential.

Storage model (no server-side case-content tables):

- CASE_SHARE overlays anchor to ``document_id="case-shares:{effective_id}"`` at
  VAULT_RECORDS_FILE — one overlay per grant, same records pattern as
  ``document_share_store``. Token format is owner-scoped
  (``{effective_user_id}:{urlsafe32}``) so a reviewer request resolves the
  owning vault with no server-side token index.

- REVIEW_THREAD overlays anchor to ``document_id="review-threads:{case_id}"``
  at VAULT_CASE_REVIEW_FILE — one overlay per document-tied Q&A thread, all
  threads for a case share the anchor so ``get_overlays`` enumerates them.
  Reviewer questions and tenant answers are messages inside the thread
  payload; ``side`` attributes authorship ("reviewer" | "tenant"). Every
  overlay is created with the owner's context (created_by = tenant), carries
  ``certified=False``, and never touches an original document.

Reviewer-side calls rebuild the owner's UserContext from the token prefix via
``build_context_for_user_id`` — the same path document_share_store uses. If
the owner's storage token is unavailable the share reads as "unavailable"
rather than erroring.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime
from types import SimpleNamespace

from app.core.id_gen import make_id
from app.core.overlay_types import OverlayType
from app.core.utc import utc_now
from app.core.user_context import UserContext, build_context_for_user_id
from app.core.vault_paths import VAULT_CASE_REVIEW_FILE, VAULT_RECORDS_FILE
from app.models.unified_overlay_models import CreateOverlayRequest
from app.services.storage import get_provider
from app.services.unified_overlay_manager import UnifiedOverlayManager, get_unified_overlay_manager

logger = logging.getLogger(__name__)

# Share lifecycle states returned to callers (view.status).
STATUS_ACTIVE = "active"
STATUS_EXPIRED = "expired"
STATUS_REVOKED = "revoked"

# Reviewer-visible sections. "documents" is backed by an explicit document id
# list; notes/deadlines are live reads scoped to the case.
SECTIONS = ("summary", "documents", "notes", "deadlines")


def _shares_anchor(effective_id: str) -> str:
    return f"case-shares:{effective_id}"


def _threads_anchor(case_id) -> str:
    return f"review-threads:{case_id}"


async def _get_manager(user: UserContext) -> UnifiedOverlayManager:
    storage = get_provider(user.provider.value, access_token=user.access_token)
    return await get_unified_overlay_manager(storage, user.get_effective_user_id())


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


# =============================================================================
# CASE_SHARE — share grants
# =============================================================================


def _share_view(overlay, owner_id: str) -> SimpleNamespace:
    p = overlay.payload
    view = SimpleNamespace(
        id=p.get("share_id") or overlay.overlay_id,
        owner_user_id=owner_id,
        case_id=p.get("case_id"),
        case_title=p.get("case_title"),
        reviewer_label=p.get("reviewer_label"),
        reviewer_contact=p.get("reviewer_contact"),
        documents=list(p.get("documents") or []),
        include_notes=bool(p.get("include_notes")),
        include_summary=bool(p.get("include_summary", True)),
        deadlines=list(p.get("deadlines") or []),
        share_token=p.get("share_token"),
        expires_at=_parse_dt(p.get("expires_at")),
        revoked_at=_parse_dt(p.get("revoked_at")),
        accessed_at=_parse_dt(p.get("accessed_at")),
        access_count=p.get("access_count") or 0,
        created_at=_parse_dt(p.get("created_at")) or overlay.created_at,
        overlay_id=overlay.overlay_id,
    )
    view.status = share_status(view)
    return view


def share_status(view) -> str:
    """Computed lifecycle state for a share view."""
    if view.revoked_at:
        return STATUS_REVOKED
    if view.expires_at and view.expires_at < utc_now():
        return STATUS_EXPIRED
    return STATUS_ACTIVE


def shared_document_ids(view) -> set[str]:
    """Vault document ids this share exposes. The enforcement set."""
    return {str(d.get("id")) for d in view.documents if d.get("id")}


async def _list_share_overlays(user: UserContext) -> list:
    manager = await _get_manager(user)
    effective_id = user.get_effective_user_id()
    response = await manager.get_overlays(
        document_id=_shares_anchor(effective_id), overlay_type=OverlayType.CASE_SHARE
    )
    if not response.success:
        logger.warning("Case-share list failed for user %s: %s", user.user_id[:8], response.message)
        return []
    return [o for o in response.overlays if o.created_by == effective_id]


async def create_share(
    user: UserContext,
    *,
    case_id,
    case_title: str | None,
    reviewer_label: str,
    reviewer_contact: str | None = None,
    documents: list[dict] | None = None,
    include_notes: bool = True,
    deadlines: list[dict] | None = None,
    include_summary: bool = True,
    expires_at: datetime | None = None,
) -> SimpleNamespace | None:
    """Create a CASE_SHARE overlay. `documents` are [{id, name}] snapshots —
    the id list is the reviewer scope boundary; names ride along so the
    reviewer page renders even if vault listing is momentarily unavailable."""
    effective_id = user.get_effective_user_id()
    manager = await _get_manager(user)

    docs = [
        {"id": str(d.get("id", "")), "name": str(d.get("name", "")).strip()}
        for d in (documents or [])
        if d.get("id")
    ]
    deadlines_clean = [
        {
            "id": str(d.get("id", "")),
            "title": str(d.get("title", "")).strip(),
            "start_datetime": d.get("start_datetime"),
        }
        for d in (deadlines or [])
        if d.get("id")
    ]
    share_token = f"{effective_id}:{secrets.token_urlsafe(32)}"
    payload = {
        "share_id": make_id("cshare"),
        "case_id": case_id,
        "case_title": case_title,
        "reviewer_label": reviewer_label.strip(),
        "reviewer_contact": (reviewer_contact or "").strip() or None,
        "documents": docs,
        "include_notes": bool(include_notes),
        "include_summary": bool(include_summary),
        "deadlines": deadlines_clean,
        "share_token": share_token,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "revoked_at": None,
        "accessed_at": None,
        "access_count": 0,
        "created_at": utc_now().isoformat(),
        "certified": False,
    }
    response = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.CASE_SHARE,
            document_id=_shares_anchor(effective_id),
            vault_path=VAULT_RECORDS_FILE,
            payload=payload,
            metadata={"scope_area": "case_shares"},
        )
    )
    if not response.success or not response.overlay_id:
        logger.error("Failed to create case share for user %s: %s", user.user_id[:8], response.message)
        return None
    overlay = await manager.get_overlay(response.overlay_id)
    return _share_view(overlay, effective_id) if overlay else None


async def list_shares(user: UserContext) -> list[SimpleNamespace]:
    """All case shares owned by the user, newest first."""
    overlays = await _list_share_overlays(user)
    overlays.sort(key=lambda o: o.payload.get("created_at") or "", reverse=True)
    effective_id = user.get_effective_user_id()
    return [_share_view(o, effective_id) for o in overlays]


async def resolve_share_with_owner(share_token: str) -> tuple[SimpleNamespace, UserContext] | None:
    """Resolve an owner-scoped share token to (share view, owner context).

    The token's owner prefix identifies the vault; no server-side index.
    Returns None for malformed tokens or owners whose context can't be
    rebuilt (storage disconnected).
    """
    owner_id, sep, _raw = share_token.rpartition(":")
    if not sep or not owner_id:
        return None
    user = await build_context_for_user_id(owner_id)
    if not user:
        return None
    effective_id = user.get_effective_user_id()
    for o in await _list_share_overlays(user):
        if o.payload.get("share_token") == share_token:
            return _share_view(o, effective_id), user
    return None


async def resolve_share(share_token: str) -> SimpleNamespace | None:
    resolved = await resolve_share_with_owner(share_token)
    return resolved[0] if resolved else None


async def revoke_share(user: UserContext, share_id: str) -> SimpleNamespace | None:
    """Set revoked_at on a share the user owns. Returns the updated view."""
    for o in await _list_share_overlays(user):
        if (o.payload.get("share_id") or o.overlay_id) == share_id:
            if o.payload.get("revoked_at"):
                return _share_view(o, user.get_effective_user_id())
            o.payload["revoked_at"] = utc_now().isoformat()
            manager = await _get_manager(user)
            await manager.update_overlay(o.overlay_id, payload=o.payload)
            return _share_view(o, user.get_effective_user_id())
    return None


async def get_share(user: UserContext, share_id: str) -> SimpleNamespace | None:
    for view in await list_shares(user):
        if view.id == share_id:
            return view
    return None


async def record_share_access(share_token: str) -> None:
    """Bump access_count/accessed_at on the share record. Best-effort."""
    resolved = await resolve_share_with_owner(share_token)
    if not resolved:
        return
    view, user = resolved
    for o in await _list_share_overlays(user):
        if o.overlay_id == view.overlay_id:
            o.payload["access_count"] = (o.payload.get("access_count") or 0) + 1
            o.payload["accessed_at"] = utc_now().isoformat()
            manager = await _get_manager(user)
            await manager.update_overlay(o.overlay_id, payload=o.payload)
            return


# =============================================================================
# REVIEW_THREAD — document-specific Q&A
# =============================================================================


def _thread_view(overlay) -> dict:
    p = overlay.payload
    return {
        "thread_id": p.get("thread_id") or overlay.overlay_id,
        "overlay_id": overlay.overlay_id,
        "share_id": p.get("share_id"),
        "case_id": p.get("case_id"),
        "document_id": p.get("document_id"),
        "document_name": p.get("document_name"),
        "subject": p.get("subject") or "",
        "status": p.get("status") or "open",
        "unread_by_tenant": bool(p.get("unread_by_tenant")),
        "unread_by_reviewer": bool(p.get("unread_by_reviewer")),
        "messages": list(p.get("messages") or []),
        "created_at": p.get("created_at"),
        "answered_at": p.get("answered_at"),
        "certified": False,
    }


async def list_threads(user: UserContext, case_id) -> list[dict]:
    """All review threads anchored to a case, oldest first."""
    manager = await _get_manager(user)
    effective_id = user.get_effective_user_id()
    response = await manager.get_overlays(
        document_id=_threads_anchor(case_id), overlay_type=OverlayType.REVIEW_THREAD
    )
    if not response.success:
        logger.warning("Review-thread list failed for user %s: %s", user.user_id[:8], response.message)
        return []
    threads = [
        _thread_view(o)
        for o in response.overlays
        if o.created_by == effective_id and o.payload.get("kind") == "thread"
    ]
    threads.sort(key=lambda t: t.get("created_at") or "")
    return threads


async def list_threads_for_share(owner: UserContext, share) -> list[dict]:
    """Threads belonging to one share, restricted to documents still in scope."""
    allowed = shared_document_ids(share)
    threads = [
        t
        for t in await list_threads(owner, share.case_id)
        if t["share_id"] == share.id and t["document_id"] in allowed
    ]
    return threads


async def list_unread_threads(user: UserContext) -> list[dict]:
    """Unread reviewer threads across all the tenant's shares (tenant panel)."""
    shares = await list_shares(user)
    unread: list[dict] = []
    for share in shares:
        if share.status != STATUS_ACTIVE:
            continue
        for t in await list_threads_for_share(user, share):
            if t["unread_by_tenant"]:
                t["reviewer_label"] = share.reviewer_label
                t["case_title"] = share.case_title
                unread.append(t)
    return unread


async def _find_thread_overlay(user: UserContext, case_id, thread_id: str):
    manager = await _get_manager(user)
    effective_id = user.get_effective_user_id()
    overlay = await manager.get_overlay(thread_id)
    if (
        overlay is not None
        and overlay.created_by == effective_id
        and overlay.overlay_type == OverlayType.REVIEW_THREAD
        and overlay.document_id == _threads_anchor(case_id)
    ):
        return overlay
    response = await manager.get_overlays(
        document_id=_threads_anchor(case_id), overlay_type=OverlayType.REVIEW_THREAD
    )
    if not response.success:
        return None
    for candidate in response.overlays:
        if candidate.created_by == effective_id and candidate.payload.get("thread_id") == thread_id:
            return candidate
    return None


def _append_message(payload: dict, side: str, body: str) -> dict:
    payload.setdefault("messages", []).append(
        {
            "id": make_id("msg"),
            "side": side,
            "body": body.strip(),
            "created_at": utc_now().isoformat(),
        }
    )
    return payload


async def post_question(
    owner: UserContext,
    share,
    *,
    document_id: str,
    body: str,
    subject: str | None = None,
) -> dict | None:
    """Reviewer posts a question against a shared document. Caller must have
    already verified the share is active and document_id is in scope. The
    overlay is created with the owner's context — tenant-owned data."""
    if document_id not in shared_document_ids(share):
        return None
    doc_name = next(
        (d["name"] for d in share.documents if str(d.get("id")) == document_id),
        "",
    )
    now = utc_now().isoformat()
    payload = {
        "kind": "thread",
        "thread_id": make_id("rth"),
        "share_id": share.id,
        "case_id": share.case_id,
        "document_id": document_id,
        "document_name": doc_name,
        "subject": (subject or "").strip(),
        "status": "open",
        "unread_by_tenant": True,
        "unread_by_reviewer": False,
        "messages": [],
        "created_at": now,
        "answered_at": None,
        "certified": False,
    }
    _append_message(payload, "reviewer", body)
    manager = await _get_manager(owner)
    response = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.REVIEW_THREAD,
            document_id=_threads_anchor(share.case_id),
            vault_path=VAULT_CASE_REVIEW_FILE,
            payload=payload,
            metadata={"scope_area": "review_threads", "share_id": share.id},
        )
    )
    if not response.success or not response.overlay_id:
        logger.error("Failed to create review thread for user %s: %s", owner.user_id[:8], response.message)
        return None
    overlay = await manager.get_overlay(response.overlay_id)
    return _thread_view(overlay) if overlay else None


async def post_message(
    user: UserContext,
    case_id,
    thread_id: str,
    *,
    side: str,
    body: str,
) -> dict | None:
    """Append a message to a thread. side="tenant" (owner reply) sets
    status=answered + unread_by_reviewer; side="reviewer" re-opens the thread
    + unread_by_tenant. Both parties' text stays their own — this store never
    generates content."""
    overlay = await _find_thread_overlay(user, case_id, thread_id)
    if overlay is None or overlay.payload.get("kind") != "thread":
        return None
    _append_message(overlay.payload, side, body)
    now = utc_now().isoformat()
    if side == "tenant":
        overlay.payload["status"] = "answered"
        overlay.payload["answered_at"] = now
        overlay.payload["unread_by_reviewer"] = True
        overlay.payload["unread_by_tenant"] = False
    else:
        overlay.payload["status"] = "open"
        overlay.payload["unread_by_tenant"] = True
        overlay.payload["unread_by_reviewer"] = False
    manager = await _get_manager(user)
    await manager.update_overlay(overlay.overlay_id, payload=overlay.payload)
    return _thread_view(overlay)


async def mark_threads_read(user: UserContext, case_id, side_read: str, share_id: str | None = None) -> None:
    """Clear the unread flag for one side across a case's threads.
    side_read="tenant" clears unread_by_tenant (tenant opened the panel);
    "reviewer" clears unread_by_reviewer (reviewer loaded threads). share_id
    scopes the clear to one share's threads — a tenant viewing share A must
    not consume the unread signal on share B's threads in the same case."""
    manager = await _get_manager(user)
    flag = "unread_by_tenant" if side_read == "tenant" else "unread_by_reviewer"
    response = await manager.get_overlays(
        document_id=_threads_anchor(case_id), overlay_type=OverlayType.REVIEW_THREAD
    )
    if not response.success:
        return
    effective_id = user.get_effective_user_id()
    for o in response.overlays:
        if share_id is not None and o.payload.get("share_id") != share_id:
            continue
        if o.created_by == effective_id and o.payload.get(flag):
            o.payload[flag] = False
            await manager.update_overlay(o.overlay_id, payload=o.payload)


async def unread_count_for_share(user: UserContext, share) -> int:
    threads = await list_threads_for_share(user, share)
    return sum(1 for t in threads if t["unread_by_tenant"])
