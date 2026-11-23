"""Legal Share — gated release + chain-of-custody service (matrix G9).

A release is the ONE way marked-up state becomes a concrete artifact:
the tenant gates a separate action that produces a NEW vault file — a
self-contained zip bundle holding the original bytes (untouched), the
DocumentProof certificate (hash + timestamp + signature + TSA token),
the color-key legend so highlights decode offline, an overlay snapshot,
and the custody log to date. The original document is never modified —
that invariant is enforced by writing only under ``VAULT_RELEASES`` and
verifying the original's sha256 before and after.

Custody model: both document identity spaces resolve to one DocRef —
``vault_index`` rows (canonical uploads, keyed by vault_id) and
``documents`` rows (setup intake / advocate surfaces, keyed by id),
correlated on ``documents.file_path == vault_index.storage_path``.
Release records are RELEASE_RECORD overlays anchored to the canonical id
(vault_id when present). The chronological custody log merges intake,
document_access_logs events, DOCUMENT_SHARE / CASE_SHARE grant overlays,
and RELEASE_RECORD releases — every recorded view/share/annotate/release
event, exportable per document (FRE 902(13)/(14) posture: platform keeps
the mechanics; certification language stays with the qualified person).
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import zipfile
from datetime import datetime
from types import SimpleNamespace

from sqlalchemy import select

from app.core.id_gen import make_id
from app.core.overlay_types import OverlayType
from app.core.utc import utc_now
from app.core.user_context import UserContext
from app.core.vault_paths import VAULT_RECORDS_FILE, VAULT_RELEASES
from app.models.unified_overlay_models import CreateOverlayRequest
from app.services.storage import get_provider
from app.services.unified_overlay_manager import UnifiedOverlayManager, get_unified_overlay_manager

logger = logging.getLogger(__name__)

# Overlay types whose payloads make sense to ship inside a release bundle —
# the marks the legend decodes. DOCUMENT_KEY travels separately as the
# legend itself.
ANNOTATION_TYPES = {
    OverlayType.HIGHLIGHT,
    OverlayType.NOTE,
    OverlayType.FOOTNOTE,
    OverlayType.TRACKED_EDIT,
}

# Fallback legend, mirroring the unified-overlays router default so an
# offline reader can decode highlight colors even when no DOCUMENT_KEY
# overlay was ever set.
DEFAULT_COLOR_KEY: dict[str, str] = {
    "yellow": "Key evidence",
    "red": "Contradiction",
    "blue": "Date or deadline",
    "green": "Money",
    "orange": "Notice or warning",
    "purple": "Personal note",
}

# =============================================================================
# DocRef — one document across both identity spaces
# =============================================================================


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


async def _find_db_document(db, doc_id: str):
    from app.models.models import Document

    result = await db.execute(select(Document).where(Document.id == doc_id))
    return result.scalars().first()


async def _find_vault_doc(vault_id: str):
    try:
        from app.services.vault_upload_service import get_vault_service

        return await get_vault_service().get_document(vault_id)
    except Exception as exc:
        logger.warning("Release: vault doc lookup failed for %s: %s", vault_id, exc)
        return None


async def _find_vault_doc_by_path(user_id: str, storage_path: str):
    try:
        from app.services.vault_upload_service import get_vault_service

        for doc in await get_vault_service().get_user_documents(user_id):
            if doc.storage_path == storage_path:
                return doc
    except Exception as exc:
        logger.warning("Release: vault list failed for %s: %s", user_id[:8], exc)
    return None


async def _find_db_document_by_path(user_id: str, storage_path: str, db):
    from app.models.models import Document

    result = await db.execute(
        select(Document).where(Document.user_id == user_id, Document.file_path == storage_path)
    )
    return result.scalars().first()


async def resolve_document(user: UserContext, doc_id: str, db) -> SimpleNamespace | None:
    """Resolve a document id from either identity space into one DocRef.

    Returns a ref carrying every known identifier for the document, or
    None when nothing resolves. The ref is NOT owner-checked — callers
    enforce ownership so the deny path can log attempts explicitly.
    """
    vault_doc = await _find_vault_doc(doc_id)
    db_doc = None
    if vault_doc is not None:
        db_doc = await _find_db_document_by_path(vault_doc.user_id, vault_doc.storage_path, db)
    else:
        db_doc = await _find_db_document(db, doc_id)
        if db_doc is not None:
            vault_doc = await _find_vault_doc_by_path(db_doc.user_id, db_doc.file_path)

    if vault_doc is None and db_doc is None:
        return None

    owner_user_id = (vault_doc.user_id if vault_doc is not None else db_doc.user_id)
    canonical_id = vault_doc.vault_id if vault_doc is not None else db_doc.id
    return SimpleNamespace(
        canonical_id=canonical_id,
        vault_id=vault_doc.vault_id if vault_doc is not None else None,
        documents_id=db_doc.id if db_doc is not None else None,
        owner_user_id=owner_user_id,
        storage_path=vault_doc.storage_path if vault_doc is not None else db_doc.file_path,
        filename=(
            (vault_doc.filename or vault_doc.safe_filename)
            if vault_doc is not None
            else (db_doc.original_filename or db_doc.filename)
        ),
        safe_filename=vault_doc.safe_filename if vault_doc is not None else (db_doc.filename or ""),
        mime_type=vault_doc.mime_type if vault_doc is not None else db_doc.mime_type,
        sha256_recorded=(vault_doc.sha256_hash if vault_doc is not None else db_doc.sha256_hash) or None,
        file_size=vault_doc.file_size if vault_doc is not None else db_doc.file_size,
        uploaded_at=_parse_dt(vault_doc.uploaded_at if vault_doc is not None else db_doc.uploaded_at),
        registry_id=getattr(vault_doc, "registry_id", None) if vault_doc is not None else None,
    )


def all_doc_ids(ref: SimpleNamespace) -> set[str]:
    """Every identifier this document answers to — overlay anchors, share
    payloads, and audit rows can carry any of them."""
    return {
        str(v)
        for v in (ref.canonical_id, ref.vault_id, ref.documents_id, ref.storage_path, ref.safe_filename)
        if v
    }


async def list_owner_documents(user: UserContext, db) -> list[SimpleNamespace]:
    """Union of the owner's vault docs and documents rows for pickers."""
    refs: dict[str, SimpleNamespace] = {}
    try:
        from app.services.vault_upload_service import get_vault_service

        for doc in await get_vault_service().get_user_documents(user.user_id):
            ref = SimpleNamespace(
                canonical_id=doc.vault_id,
                vault_id=doc.vault_id,
                documents_id=None,
                owner_user_id=doc.user_id,
                storage_path=doc.storage_path,
                filename=doc.filename or doc.safe_filename,
                safe_filename=doc.safe_filename,
                mime_type=doc.mime_type,
                sha256_recorded=doc.sha256_hash or None,
                file_size=doc.file_size,
                uploaded_at=_parse_dt(doc.uploaded_at),
                registry_id=getattr(doc, "registry_id", None),
            )
            refs[doc.vault_id] = ref
    except Exception as exc:
        logger.warning("Release: vault list failed for %s: %s", user.user_id[:8], exc)

    from app.models.models import Document

    result = await db.execute(select(Document).where(Document.user_id == user.user_id))
    for db_doc in result.scalars().all():
        matched = next((r for r in refs.values() if r.storage_path == db_doc.file_path), None)
        if matched is not None:
            matched.documents_id = db_doc.id
            if not matched.sha256_recorded:
                matched.sha256_recorded = db_doc.sha256_hash
        else:
            refs[db_doc.id] = SimpleNamespace(
                canonical_id=db_doc.id,
                vault_id=None,
                documents_id=db_doc.id,
                owner_user_id=db_doc.user_id,
                storage_path=db_doc.file_path,
                filename=db_doc.original_filename or db_doc.filename,
                safe_filename=db_doc.filename or "",
                mime_type=db_doc.mime_type,
                sha256_recorded=db_doc.sha256_hash or None,
                file_size=db_doc.file_size,
                uploaded_at=_parse_dt(db_doc.uploaded_at),
                registry_id=None,
            )
    return sorted(refs.values(), key=lambda r: r.uploaded_at or datetime.min, reverse=True)


# =============================================================================
# Storage + overlay access
# =============================================================================


async def _storage_for(user: UserContext):
    return get_provider(user.provider.value, access_token=user.access_token)


async def _manager_for(user: UserContext) -> UnifiedOverlayManager:
    storage = await _storage_for(user)
    return await get_unified_overlay_manager(storage, user.get_effective_user_id())


async def fetch_document_bytes(user: UserContext, ref: SimpleNamespace) -> bytes | None:
    """Read the original bytes. Read-only — nothing on this path writes."""
    if ref.vault_id:
        try:
            from app.services.vault_upload_service import get_vault_service

            content = await get_vault_service().get_document_content(
                ref.vault_id, access_token=user.access_token
            )
            if content:
                return content
        except Exception as exc:
            logger.warning("Release: vault content fetch failed for %s: %s", ref.vault_id, exc)
    try:
        storage = await _storage_for(user)
        return await storage.download_file(ref.storage_path)
    except Exception as exc:
        logger.warning("Release: storage download failed for %s: %s", ref.canonical_id, exc)
        return None


async def _overlays_for_doc(user: UserContext, ref: SimpleNamespace) -> list:
    """All overlays anchored to any of the document's identifiers."""
    manager = await _manager_for(user)
    seen: set[str] = set()
    overlays: list = []
    for anchor in sorted(all_doc_ids(ref)):
        try:
            response = await manager.get_overlays(document_id=anchor)
        except Exception as exc:
            logger.warning("Release: overlay list failed for %s anchor %s: %s", ref.canonical_id, anchor, exc)
            continue
        if not response.success:
            continue
        for overlay in response.overlays:
            if overlay.overlay_id not in seen:
                seen.add(overlay.overlay_id)
                overlays.append(overlay)
    return overlays


async def gather_legend(user: UserContext, ref: SimpleNamespace) -> dict:
    """The document's color legend — stored DOCUMENT_KEY meanings merged over
    the default palette, plus a flag so readers know when it's the default."""
    colors = dict(DEFAULT_COLOR_KEY)
    found = False
    for overlay in await _overlays_for_doc(user, ref):
        if overlay.overlay_type != OverlayType.DOCUMENT_KEY:
            continue
        found = True
        payload_colors = (overlay.payload or {}).get("colors")
        if isinstance(payload_colors, dict):
            for key, value in payload_colors.items():
                if key in DEFAULT_COLOR_KEY and str(value).strip():
                    colors[key] = str(value).strip()
    return {"colors": colors, "is_default": not found}


async def gather_annotations(user: UserContext, ref: SimpleNamespace) -> list[dict]:
    """Snapshot of the document's annotation overlays for offline decode."""
    out: list[dict] = []
    for overlay in await _overlays_for_doc(user, ref):
        if overlay.overlay_type not in ANNOTATION_TYPES:
            continue
        out.append(
            {
                "overlay_id": overlay.overlay_id,
                "overlay_type": overlay.overlay_type.value,
                "created_by": overlay.created_by,
                "created_at": overlay.created_at.isoformat() if overlay.created_at else None,
                "payload": overlay.payload,
            }
        )
    out.sort(key=lambda a: a.get("created_at") or "")
    return out


# =============================================================================
# Custody log (G9.6) — chronological, exportable
# =============================================================================


def _event(timestamp, event: str, actor: str | None, detail: str, outcome: str = "ok") -> dict:
    return {
        "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp,
        "event": event,
        "actor": actor,
        "outcome": outcome,
        "detail": detail,
    }


async def build_custody_log(user: UserContext, ref: SimpleNamespace, db) -> list[dict]:
    """Chronological per-document custody record.

    Sources: intake metadata, document_access_logs (cross-party access —
    every advocate/legal view, annotate, review, denied attempt, plus
    release + release_denied rows written by this module), DOCUMENT_SHARE
    and CASE_SHARE grant overlays, and RELEASE_RECORD releases.
    """
    from app.models.models import DocumentAccessLog

    owner = user.get_effective_user_id()
    ids = all_doc_ids(ref)
    events: list[dict] = []

    events.append(
        _event(
            ref.uploaded_at,
            "intake",
            ref.owner_user_id,
            f"Document received; sha256 recorded ({(ref.sha256_recorded or 'unknown')[:16]}…)",
        )
    )

    # Cross-party access rows (advocate/legal views, annotates, releases,
    # denied attempts — and any doc-scoped share events on this document).
    result = await db.execute(
        select(DocumentAccessLog).where(
            DocumentAccessLog.tenant_user_id == ref.owner_user_id,
            DocumentAccessLog.document_id.in_(sorted(ids)),
        )
    )
    for row in result.scalars().all():
        events.append(
            _event(
                row.timestamp,
                row.action,
                row.actor_user_id,
                row.detail or "",
                outcome=row.outcome or "ok",
            )
        )

    # Share grants covering this document (DOCUMENT_SHARE + CASE_SHARE
    # overlays in the owner's vault — the grants are custody events too).
    try:
        manager = await _manager_for(user)
        for anchor, otype in (
            (f"shares:{owner}", OverlayType.DOCUMENT_SHARE),
            (f"case-shares:{owner}", OverlayType.CASE_SHARE),
        ):
            response = await manager.get_overlays(document_id=anchor, overlay_type=otype)
            if not response.success:
                continue
            for overlay in response.overlays:
                p = overlay.payload or {}
                if otype == OverlayType.DOCUMENT_SHARE:
                    hit = str(p.get("vault_id")) in ids
                    label = p.get("recipient_identifier") or "recipient"
                    kind = "share_created"
                else:
                    shared_ids = {str(d.get("id")) for d in (p.get("documents") or []) if d.get("id")}
                    hit = bool(shared_ids & ids)
                    label = p.get("reviewer_label") or "reviewer"
                    kind = "case_share_created"
                if not hit:
                    continue
                detail = f"Shared with {label}"
                if p.get("revoked_at"):
                    events.append(_event(_parse_dt(p.get("revoked_at")), "share_revoked", owner, detail))
                events.append(
                    _event(
                        _parse_dt(p.get("created_at")) or overlay.created_at,
                        kind,
                        owner,
                        detail,
                    )
                )
    except Exception as exc:
        logger.warning("Release: share-event scan failed for %s: %s", ref.canonical_id, exc)

    # Releases of this document.
    for record in await list_releases(user, ref):
        events.append(
            _event(
                _parse_dt(record.get("released_at")),
                "release",
                record.get("released_by"),
                f"Released copy {record.get('release_id')} "
                f"(artifact sha256 {(record.get('artifact_sha256') or '')[:16]}…)",
            )
        )

    events.sort(key=lambda e: e["timestamp"] or "")
    return events


# =============================================================================
# Release records (RELEASE_RECORD overlays)
# =============================================================================


def _release_view(overlay) -> dict:
    p = overlay.payload or {}
    return {
        "release_id": p.get("release_id") or overlay.overlay_id,
        "overlay_id": overlay.overlay_id,
        "document_id": p.get("document_id"),
        "artifact_path": p.get("artifact_path"),
        "artifact_name": p.get("artifact_name"),
        "artifact_sha256": p.get("artifact_sha256"),
        "artifact_size": p.get("artifact_size"),
        "original_sha256": p.get("original_sha256"),
        "intake_sha256": p.get("intake_sha256"),
        "hash_verified_against_intake": p.get("hash_verified_against_intake"),
        "released_at": p.get("released_at"),
        "released_by": p.get("released_by"),
        "certificate": p.get("certificate"),
        "legend": p.get("legend"),
        "custody_event_count": p.get("custody_event_count"),
    }


async def list_releases(user: UserContext, ref: SimpleNamespace) -> list[dict]:
    """Every release record for this document, oldest first."""
    manager = await _manager_for(user)
    out: list[dict] = []
    seen: set[str] = set()
    for anchor in sorted(all_doc_ids(ref)):
        try:
            response = await manager.get_overlays(
                document_id=anchor, overlay_type=OverlayType.RELEASE_RECORD
            )
        except Exception as exc:
            logger.warning("Release: record list failed for %s: %s", anchor, exc)
            continue
        if not response.success:
            continue
        for overlay in response.overlays:
            if overlay.overlay_id not in seen:
                seen.add(overlay.overlay_id)
                out.append(_release_view(overlay))
    out.sort(key=lambda r: r.get("released_at") or "")
    return out


# =============================================================================
# The gated release (G9.1, G9.2, G9.5)
# =============================================================================


def _safe_name(name: str) -> str:
    cleaned = re.sub(r"[^\w\-. ]", "_", name or "document").strip()
    return cleaned or "document"


def _bundle_readme(ref: SimpleNamespace, record: dict) -> str:
    return (
        "What this file is\n"
        "=================\n\n"
        "A released copy of one document, produced by Semptify at the document\n"
        "owner's explicit request. It does NOT replace or modify the original\n"
        "document — the original stays untouched in the owner's vault.\n\n"
        "Contents:\n"
        "  document/         the original file, byte-for-byte\n"
        "  certificate.json  hash (SHA-256), timestamp, and signed proof\n"
        "  legend.json       what each highlight color means (decodes overlays.json)\n"
        "  overlays.json     every note/highlight/footnote on the document\n"
        "  custody-log.json  who did what to this document, in order\n"
        "  release.json      the release manifest\n\n"
        f"Document: {ref.filename}\n"
        f"Original SHA-256: {record['document']['original_sha256']}\n"
        f"Released at: {record['released_at']}\n"
        f"Release id: {record['release_id']}\n"
    )


async def release_document(user: UserContext, ref: SimpleNamespace, db) -> dict:
    """Produce the released artifact. Owner-only — callers enforce that.

    Steps: fetch original bytes → recompute sha256 and compare to the intake
    record → snapshot legend + overlays + custody → stamp a DocumentProof
    (timestamp + signature + TSA token) → zip the bundle → write it under
    VAULT_RELEASES → record a RELEASE_RECORD overlay → verify the original
    on disk still matches its recorded hash.
    """
    from app.services.storage.legal_integrity import get_legal_integrity

    owner_id = user.get_effective_user_id()

    original = await fetch_document_bytes(user, ref)
    if original is None:
        raise RuntimeError("document_bytes_unavailable")
    original_sha256 = hashlib.sha256(original).hexdigest()
    hash_verified = ref.sha256_recorded is None or ref.sha256_recorded == original_sha256

    legend = await gather_legend(user, ref)
    annotations = await gather_annotations(user, ref)
    custody = await build_custody_log(user, ref, db)

    integrity = get_legal_integrity(owner_id)
    proof = await integrity.create_document_proof(
        original,
        action="release",
        metadata={
            "document_id": ref.canonical_id,
            "vault_id": ref.vault_id,
            "documents_id": ref.documents_id,
            "filename": ref.filename,
        },
    )

    release_id = make_id("rls")
    released_at = utc_now().isoformat()
    manifest = {
        "release_id": release_id,
        "released_at": released_at,
        "released_by": owner_id,
        "document": {
            "canonical_id": ref.canonical_id,
            "vault_id": ref.vault_id,
            "documents_id": ref.documents_id,
            "filename": ref.filename,
            "mime_type": ref.mime_type,
            "file_size": ref.file_size,
            "original_sha256": original_sha256,
            "intake_sha256": ref.sha256_recorded,
            "uploaded_at": ref.uploaded_at.isoformat() if ref.uploaded_at else None,
            "registry_id": ref.registry_id,
        },
        "certificate": proof.to_dict(),
        "hash_verified_against_intake": hash_verified,
        "bundle_contents": [
            "document/" + _safe_name(ref.filename),
            "certificate.json",
            "legend.json",
            "overlays.json",
            "custody-log.json",
            "release.json",
            "README.txt",
        ],
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.txt", _bundle_readme(ref, manifest))
        zf.writestr(f"document/{_safe_name(ref.filename)}", original)
        zf.writestr("certificate.json", json.dumps(proof.to_dict(), indent=2, default=str))
        zf.writestr("legend.json", json.dumps(legend, indent=2))
        zf.writestr("overlays.json", json.dumps(annotations, indent=2, default=str))
        zf.writestr("custody-log.json", json.dumps(custody, indent=2, default=str))
        zf.writestr("release.json", json.dumps(manifest, indent=2, default=str))
    bundle = buf.getvalue()
    artifact_sha256 = hashlib.sha256(bundle).hexdigest()

    artifact_name = f"{_safe_name(release_id)}-{_safe_name(ref.filename)}.zip"
    storage = await _storage_for(user)
    uploaded = await storage.upload_file(
        file_content=bundle,
        destination_path=f"{VAULT_RELEASES}/{ref.canonical_id}",
        filename=artifact_name,
        mime_type="application/zip",
    )
    artifact_path = getattr(uploaded, "path", None) or f"{VAULT_RELEASES}/{ref.canonical_id}/{artifact_name}"

    manager = await _manager_for(user)
    payload = {
        "kind": "release",
        "release_id": release_id,
        "document_id": ref.canonical_id,
        "vault_id": ref.vault_id,
        "documents_id": ref.documents_id,
        "filename": ref.filename,
        "artifact_path": artifact_path,
        "artifact_name": artifact_name,
        "artifact_sha256": artifact_sha256,
        "artifact_size": len(bundle),
        "original_sha256": original_sha256,
        "intake_sha256": ref.sha256_recorded,
        "hash_verified_against_intake": hash_verified,
        "released_at": released_at,
        "released_by": owner_id,
        "certificate": proof.to_dict(),
        "legend": legend,
        "custody_event_count": len(custody),
        "certified": False,
    }
    response = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.RELEASE_RECORD,
            document_id=ref.canonical_id,
            vault_path=ref.storage_path or VAULT_RECORDS_FILE,
            payload=payload,
            metadata={"scope_area": "releases"},
        )
    )
    if not response.success or not response.overlay_id:
        raise RuntimeError(f"release_record_failed:{response.message}")

    # Overlay-only invariant check: re-read the original bytes after the
    # release and confirm the recorded hash still matches. If this ever
    # fails the release is invalid — surface it, don't mask it.
    after = await fetch_document_bytes(user, ref)
    original_intact = after is not None and hashlib.sha256(after).hexdigest() == original_sha256

    record = _release_view(await manager.get_overlay(response.overlay_id))
    record["hash_verified_against_intake"] = hash_verified
    record["original_intact_after_release"] = original_intact
    record["artifact_bytes_available"] = True
    return record


async def fetch_release_artifact(user: UserContext, ref: SimpleNamespace, release_id: str) -> tuple[bytes, str] | None:
    """Download a released bundle. Returns (bytes, filename)."""
    for record in await list_releases(user, ref):
        if record["release_id"] != release_id:
            continue
        path = record.get("artifact_path")
        if not path:
            return None
        try:
            storage = await _storage_for(user)
            data = await storage.download_file(path)
        except Exception as exc:
            logger.warning("Release: artifact download failed for %s: %s", path, exc)
            return None
        return data, record.get("artifact_name") or f"{release_id}.zip"
    return None


async def integrity_status(user: UserContext, ref: SimpleNamespace, db) -> dict:
    """Hash lifecycle for one document — the G9.5 proof surface.

    The intake hash is on the record; this recomputes it live from the
    stored bytes so it can be checked at any time, and pairs it with the
    document's releases (whose artifact hash + timestamp + certificate
    travel together in each record).
    """
    original = await fetch_document_bytes(user, ref)
    recomputed = hashlib.sha256(original).hexdigest() if original is not None else None
    return {
        "document_id": ref.canonical_id,
        "vault_id": ref.vault_id,
        "documents_id": ref.documents_id,
        "filename": ref.filename,
        "intake_sha256": ref.sha256_recorded,
        "recomputed_sha256": recomputed,
        "matches_intake": (
            None if recomputed is None or ref.sha256_recorded is None else recomputed == ref.sha256_recorded
        ),
        "bytes_available": original is not None,
        "checked_at": utc_now().isoformat(),
        "releases": await list_releases(user, ref),
        "custody_log": await build_custody_log(user, ref, db),
    }
