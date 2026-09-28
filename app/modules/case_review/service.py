"""Case Review service — EVIDENCE_INDEX overlays in the tenant's cloud vault.

Spec: Case File Review & Evidence Index (locked 2026-09-27). One overlay
type, four payload kinds discriminated by ``payload["kind"]``:

- ``legend``        — per-case color legend. One overlay per case; entries
                      are ``[{label, color}]`` and are user-editable. Color
                      is purely visual (highlight ↔ footnote matching) and
                      carries no semantic meaning.
- ``note``          — EvidenceNote: free text plus ``links`` —
                      ``[{document_id, vault_path, name, location}]`` so one
                      entry can point at several places across several
                      documents. ``certified`` is hardcoded False; nothing
                      this module produces is ever certified.
- ``doc_tag``       — category + evidence_type pair on a vault document
                      within this case (metadata tagging only — the tenant's
                      actual cloud folders are never restructured).
- ``share_marker``  — materializes the ``legal_share_initialized``
                      capability-flag event (tenant self-declares that they
                      have shared their case file with a legal reviewer).

Anchors: ``document_id="evidence-index:{case_id}"`` (per case) and
``document_id="evidence-index:global"`` for the case-independent share
marker, both at VAULT_CASE_REVIEW_FILE. Cases are INCIDENT records —
``case_id`` is the integer ``incident_id``.
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.core.id_gen import make_id
from app.core.overlay_types import OverlayType
from app.core.user_context import UserContext
from app.core.utc import utc_now
from app.core.vault_paths import VAULT_CASE_REVIEW_FILE
from app.models.unified_overlay_models import CreateOverlayRequest, UnifiedOverlay
from app.services.incident_store import get_incident
from app.services.storage import get_provider
from app.services.unified_overlay_manager import UnifiedOverlayManager, get_unified_overlay_manager

logger = logging.getLogger(__name__)

# Capability flag event — the module stays locked until the tenant marks that
# they have shared their case file with a legal reviewer (sharing itself
# happens outside Semptify, in the tenant's own storage provider).
LEGAL_SHARE_INITIALIZED = "legal_share_initialized"

# Locked taxonomy (spec §2). Values are metadata tags only — they never move
# or rename the tenant's actual cloud files.
CATEGORIES: tuple[str, ...] = ("foundational", "discovery", "motion", "evidence", "misc")
EVIDENCE_TYPES: tuple[str, ...] = ("none", "documentary", "digital", "physical", "witness")

CATEGORY_LABELS: dict[str, str] = {
    "foundational": "Foundational",
    "discovery": "Discovery",
    "motion": "Motions",
    "evidence": "Evidence",
    "misc": "Misc",
}
EVIDENCE_TYPE_LABELS: dict[str, str] = {
    "none": "—",
    "documentary": "Documentary",
    "digital": "Digital",
    "physical": "Physical",
    "witness": "Witness statement",
}

# Starting legend (spec §3: defined per case at case start, editable).
DEFAULT_LEGEND: tuple[dict[str, str], ...] = (
    {"label": "Key fact", "color": "#f2d16b"},
    {"label": "Date or deadline", "color": "#9db8d9"},
    {"label": "Disputed or needs a closer look", "color": "#d98f8f"},
    {"label": "Money amount", "color": "#9fbf9f"},
)

_NOTE_KINDS = ("legend", "note", "doc_tag", "share_marker")


def _anchor(case_id) -> str:
    return f"evidence-index:{case_id}"


_GLOBAL_ANCHOR = "evidence-index:global"


async def _get_manager(user: UserContext) -> UnifiedOverlayManager:
    """Manager keyed to the effective user so impersonation writes belong to the tenant."""
    storage = get_provider(user.provider.value, access_token=user.access_token)
    return await get_unified_overlay_manager(storage, user.get_effective_user_id())


def _owns(effective_id: str, overlay: UnifiedOverlay) -> bool:
    return overlay.overlay_type == OverlayType.EVIDENCE_INDEX and overlay.created_by == effective_id


def _to_iso(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


async def _list_overlays(user: UserContext, anchor: str) -> list[UnifiedOverlay]:
    manager = await _get_manager(user)
    response = await manager.get_overlays(document_id=anchor, overlay_type=OverlayType.EVIDENCE_INDEX)
    if not response.success:
        logger.warning("Case review overlay list failed for user %s: %s", user.user_id[:8], response.message)
        return []
    effective_id = user.get_effective_user_id()
    return [o for o in response.overlays if _owns(effective_id, o)]


async def _create(user: UserContext, anchor: str, kind: str, payload: dict) -> UnifiedOverlay | None:
    manager = await _get_manager(user)
    payload = {k: _to_iso(v) for k, v in payload.items()}
    payload["kind"] = kind
    payload["certified"] = False  # structural guarantee — never agent-configurable
    response = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.EVIDENCE_INDEX,
            document_id=anchor,
            vault_path=VAULT_CASE_REVIEW_FILE,
            payload=payload,
            metadata={"scope": "case_review", "kind": kind},
        )
    )
    if not response.success or not response.overlay_id:
        logger.error("Failed to create case-review %s for user %s: %s", kind, user.user_id[:8], response.message)
        return None
    return await manager.get_overlay(response.overlay_id)


async def _resolve(user: UserContext, anchor: str, overlay_id: str) -> UnifiedOverlay | None:
    """Ownership-checked lookup by overlay_id or payload id within a case anchor."""
    effective_id = user.get_effective_user_id()
    manager = await _get_manager(user)
    overlay = await manager.get_overlay(overlay_id)
    if overlay is not None and _owns(effective_id, overlay) and overlay.document_id == anchor:
        return overlay
    for candidate in await _list_overlays(user, anchor):
        if candidate.payload.get("id") == overlay_id:
            return candidate
    return None


# =============================================================================
# Case resolution (cases are INCIDENT records)
# =============================================================================


async def resolve_case(user: UserContext, case_id):
    """Return the incident for case_id, or None if it isn't the tenant's."""
    return await get_incident(user, case_id)


# =============================================================================
# Share marker — the legal_share_initialized flag
# =============================================================================


async def is_share_initialized(user: UserContext, case_id=None) -> bool:
    """True if the tenant has marked a legal-share for this case or globally."""
    for o in await _list_overlays(user, _GLOBAL_ANCHOR):
        if o.payload.get("kind") == "share_marker":
            return True
    if case_id is not None:
        for o in await _list_overlays(user, _anchor(case_id)):
            if o.payload.get("kind") == "share_marker":
                return True
    return False


async def mark_share_initialized(user: UserContext, case_id=None) -> UnifiedOverlay | None:
    """Record the legal_share_initialized event. Idempotent per anchor."""
    anchor = _anchor(case_id) if case_id is not None else _GLOBAL_ANCHOR
    for o in await _list_overlays(user, anchor):
        if o.payload.get("kind") == "share_marker":
            return o
    return await _create(
        user,
        anchor,
        "share_marker",
        {
            "id": make_id("shr"),
            "case_id": case_id,
            "event": LEGAL_SHARE_INITIALIZED,
            "marked_at": utc_now().isoformat(),
        },
    )


# =============================================================================
# Legend — one overlay per case
# =============================================================================


async def _find_legend(user: UserContext, case_id) -> UnifiedOverlay | None:
    for o in await _list_overlays(user, _anchor(case_id)):
        if o.payload.get("kind") == "legend":
            return o
    return None


async def get_legend(user: UserContext, case_id) -> list[dict]:
    """Legend entries for the case — stored set, or the default starter set."""
    overlay = await _find_legend(user, case_id)
    if overlay is None:
        return [dict(e) for e in DEFAULT_LEGEND]
    return list(overlay.payload.get("entries") or [])


async def set_legend(user: UserContext, case_id, entries: list[dict]) -> list[dict]:
    """Replace the case legend (entries: [{label, color}])."""
    cleaned = [
        {"label": str(e.get("label", "")).strip(), "color": str(e.get("color", "")).strip()}
        for e in entries
        if str(e.get("label", "")).strip()
    ]
    overlay = await _find_legend(user, case_id)
    now = utc_now().isoformat()
    if overlay is not None:
        overlay.payload["entries"] = cleaned
        overlay.payload["updated_at"] = now
        manager = await _get_manager(user)
        await manager.update_overlay(overlay.overlay_id, payload=overlay.payload)
        return cleaned
    await _create(
        user,
        _anchor(case_id),
        "legend",
        {"id": make_id("lgn"), "case_id": case_id, "entries": cleaned, "created_at": now, "updated_at": now},
    )
    return cleaned


# =============================================================================
# Document tags — category + evidence_type per document per case
# =============================================================================


async def _find_tag(user: UserContext, case_id, document_id: str) -> UnifiedOverlay | None:
    for o in await _list_overlays(user, _anchor(case_id)):
        if o.payload.get("kind") == "doc_tag" and o.payload.get("document_id") == document_id:
            return o
    return None


async def get_tags(user: UserContext, case_id) -> dict[str, dict]:
    """{document_id: {category, evidence_type, name, vault_path}} for the case."""
    tags: dict[str, dict] = {}
    for o in await _list_overlays(user, _anchor(case_id)):
        p = o.payload
        if p.get("kind") == "doc_tag" and p.get("document_id"):
            tags[p["document_id"]] = {
                "category": p.get("category") or "misc",
                "evidence_type": p.get("evidence_type") or "none",
                "name": p.get("name"),
                "vault_path": p.get("vault_path"),
            }
    return tags


async def set_tag(
    user: UserContext,
    case_id,
    document_id: str,
    category: str,
    evidence_type: str,
    name: str | None = None,
    vault_path: str | None = None,
) -> dict | None:
    """Set/update a document's tag. Returns the stored tag dict."""
    if category not in CATEGORIES or evidence_type not in EVIDENCE_TYPES:
        return None
    tag = {
        "category": category,
        "evidence_type": evidence_type,
        "name": name,
        "vault_path": vault_path,
    }
    overlay = await _find_tag(user, case_id, document_id)
    now = utc_now().isoformat()
    if overlay is not None:
        overlay.payload.update(tag)
        overlay.payload["updated_at"] = now
        manager = await _get_manager(user)
        await manager.update_overlay(overlay.overlay_id, payload=overlay.payload)
        return tag
    created = await _create(
        user,
        _anchor(case_id),
        "doc_tag",
        {
            "id": make_id("tag"),
            "case_id": case_id,
            "document_id": document_id,
            **tag,
            "created_at": now,
            "updated_at": now,
        },
    )
    return tag if created else None


async def remove_tag(user: UserContext, case_id, document_id: str) -> bool:
    overlay = await _find_tag(user, case_id, document_id)
    if overlay is None:
        return False
    manager = await _get_manager(user)
    return await manager.delete_overlay(overlay.overlay_id)


# =============================================================================
# Evidence notes — free text + multi-document links
# =============================================================================


def _note_view(o: UnifiedOverlay) -> dict:
    p = o.payload
    links = p.get("links") or []
    return {
        "id": p.get("id") or o.overlay_id,
        "overlay_id": o.overlay_id,
        "links": links,
        "document_ids": [l.get("document_id") for l in links if l.get("document_id")],
        "legend_label": p.get("legend_label") or "",
        "text": p.get("text") or "",
        "certified": False,
        "created_at": p.get("created_at"),
        "updated_at": p.get("updated_at"),
    }


async def list_notes(user: UserContext, case_id) -> list[dict]:
    notes = [
        _note_view(o)
        for o in await _list_overlays(user, _anchor(case_id))
        if o.payload.get("kind") == "note"
    ]
    notes.sort(key=lambda n: n.get("created_at") or "")
    return notes


async def create_note(
    user: UserContext,
    case_id,
    text: str,
    links: list[dict] | None = None,
    legend_label: str | None = None,
) -> dict | None:
    """links: [{document_id, vault_path?, name?, location?}] — one note can
    point at several places across several documents."""
    cleaned_links = [
        {
            "document_id": str(l.get("document_id", "")),
            "vault_path": l.get("vault_path"),
            "name": l.get("name"),
            "location": str(l.get("location", "")).strip(),
        }
        for l in (links or [])
        if l.get("document_id")
    ]
    now = utc_now().isoformat()
    overlay = await _create(
        user,
        _anchor(case_id),
        "note",
        {
            "id": make_id("evn"),
            "case_id": case_id,
            "links": cleaned_links,
            "legend_label": (legend_label or "").strip(),
            "text": text.strip(),
            "created_at": now,
            "updated_at": now,
        },
    )
    return _note_view(overlay) if overlay else None


async def update_note(
    user: UserContext,
    case_id,
    note_id: str,
    text: str | None = None,
    links: list[dict] | None = None,
    legend_label: str | None = None,
) -> dict | None:
    overlay = await _resolve(user, _anchor(case_id), note_id)
    if overlay is None or overlay.payload.get("kind") != "note":
        return None
    if text is not None:
        overlay.payload["text"] = text.strip()
    if legend_label is not None:
        overlay.payload["legend_label"] = legend_label.strip()
    if links is not None:
        overlay.payload["links"] = [
            {
                "document_id": str(l.get("document_id", "")),
                "vault_path": l.get("vault_path"),
                "name": l.get("name"),
                "location": str(l.get("location", "")).strip(),
            }
            for l in links
            if l.get("document_id")
        ]
    overlay.payload["certified"] = False
    overlay.payload["updated_at"] = utc_now().isoformat()
    manager = await _get_manager(user)
    await manager.update_overlay(overlay.overlay_id, payload=overlay.payload)
    return _note_view(overlay)


async def delete_note(user: UserContext, case_id, note_id: str) -> bool:
    overlay = await _resolve(user, _anchor(case_id), note_id)
    if overlay is None or overlay.payload.get("kind") != "note":
        return False
    manager = await _get_manager(user)
    return await manager.delete_overlay(overlay.overlay_id)


# =============================================================================
# Evidence index — assembled state + paste-ready export
# =============================================================================


async def build_index(user: UserContext, case_id, documents: list[dict] | None = None) -> dict:
    """Full per-case state: legend, notes, tags, share flag."""
    anchor = _anchor(case_id)
    overlays = await _list_overlays(user, anchor)
    legend_overlay = next((o for o in overlays if o.payload.get("kind") == "legend"), None)
    legend = (
        list(legend_overlay.payload.get("entries") or [])
        if legend_overlay is not None
        else [dict(e) for e in DEFAULT_LEGEND]
    )
    notes = [_note_view(o) for o in overlays if o.payload.get("kind") == "note"]
    notes.sort(key=lambda n: n.get("created_at") or "")
    tags: dict[str, dict] = {}
    for o in overlays:
        p = o.payload
        if p.get("kind") == "doc_tag" and p.get("document_id"):
            tags[p["document_id"]] = {
                "category": p.get("category") or "misc",
                "evidence_type": p.get("evidence_type") or "none",
                "name": p.get("name"),
                "vault_path": p.get("vault_path"),
            }
    shared = any(o.payload.get("kind") == "share_marker" for o in overlays)
    if not shared:
        shared = await is_share_initialized(user)
    return {
        "case_id": case_id,
        "legend": legend,
        "notes": notes,
        "tags": tags,
        "documents": documents if documents is not None else [],
        "share_initialized": shared,
    }


def render_index_text(case_title: str, index: dict, doc_names: dict[str, str]) -> str:
    """Paste-ready plain-text evidence index for an attorney session."""
    legend_by_label = {e["label"]: e.get("color", "") for e in index.get("legend") or []}
    lines: list[str] = []
    lines.append(f"EVIDENCE INDEX — {case_title}")
    lines.append(f"Generated {utc_now().date().isoformat()} — working notes, not certified records")
    lines.append("")
    if legend_by_label:
        lines.append("Legend:")
        for label in legend_by_label:
            lines.append(f"  - {label}")
        lines.append("")
    tags = index.get("tags") or {}
    if tags:
        lines.append("Documents by category:")
        for category in CATEGORIES:
            docs = [d for d, t in tags.items() if t.get("category") == category]
            if not docs:
                continue
            lines.append(f"  {CATEGORY_LABELS[category]}:")
            for doc_id in docs:
                name = doc_names.get(doc_id) or tags[doc_id].get("name") or doc_id
                etype = tags[doc_id].get("evidence_type") or "none"
                suffix = f" ({EVIDENCE_TYPE_LABELS[etype]})" if etype != "none" else ""
                lines.append(f"    - {name}{suffix}")
        lines.append("")
    notes = index.get("notes") or []
    if notes:
        lines.append("Evidence notes:")
        for i, note in enumerate(notes, 1):
            label = note.get("legend_label")
            heading = f"{i}. [{label}] " if label else f"{i}. "
            lines.append(f"{heading}{note.get('text', '')}")
            for link in note.get("links") or []:
                doc_id = link.get("document_id")
                name = doc_names.get(doc_id) or link.get("name") or doc_id
                loc = link.get("location") or ""
                loc_part = f", {loc}" if loc else ""
                lines.append(f"       see: {name}{loc_part}")
        lines.append("")
    if not tags and not notes:
        lines.append("(no tagged documents or notes yet)")
    return "\n".join(lines)
