"""Document Center API — DC-specific endpoints for the 3-pane viewer.

Lifecycle: stable (all roles).

Endpoints
---------
GET  /api/dc/list                      — vault docs with overlay status for left pane
GET  /api/dc/document/{vault_id}/overlays — real overlay progress from UnifiedOverlayManager
GET  /api/dc/document/{vault_id}/view    — inline file stream for viewer iframe
GET  /api/dc/unlocks                    — feature unlock thresholds across all docs
POST /api/dc/document/{vault_id}/type    — set/correct document type from viewer dropdown

Overlay Integration (2026-06-29):
  The DC right panel reads REAL overlays from UnifiedOverlayManager.get_overlays()
  in the user's cloud storage. No DB fallback. If no real overlays exist, the
  endpoint returns status='processing_incomplete' and the frontend shows a
  'try again' message. This enforces the mandate: no user data is served from
  our PostgreSQL — only from the user's cloud.
"""
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.cookie_auth import verify_user_id
from app.core.user_id import COOKIE_USER_ID
from app.core.utc import utc_now
from app.core.overlay_types import OverlayType

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Document Center"])

ALLOWED_DOCUMENT_TYPES: frozenset[str] = frozenset({
    "lease",
    "notice_to_vacate",
    "repair_request",
    "rent_receipt",
    "move_in_inspection",
    "court_summons",
    "correspondence",
    "other",
})


def _auth(request: Request) -> str | None:
    """Return verified user_id from cookie, or None if unauthenticated."""
    cookie_value = request.cookies.get(COOKIE_USER_ID)
    if not cookie_value:
        return None
    return verify_user_id(cookie_value)


# ===========================================================================
# Real Overlay Fetch — reads from UnifiedOverlayManager (cloud storage)
# ===========================================================================

async def _fetch_real_overlays(doc, user_id: str) -> list:
    """Fetch real overlays for a document from UnifiedOverlayManager.

    Overlays are keyed by document_id = doc.safe_filename (set at upload time
    in vault_upload_service.py:502). Returns a list of UnifiedOverlay objects,
    or empty list on any failure (cloud unavailable, no overlays, etc.).
    """
    if doc.storage_provider == "local":
        return []  # local storage has no overlay system

    try:
        from app.core.oauth_token_manager import get_valid_token_for_user
        from app.services.storage import get_provider
        from app.services.unified_overlay_manager import get_unified_overlay_manager

        access_token = get_valid_token_for_user(user_id)
        if not access_token:
            return []

        storage = get_provider(doc.storage_provider, access_token=access_token)
        manager = await get_unified_overlay_manager(storage, user_id)
        response = await manager.get_overlays(document_id=doc.safe_filename)
        if response.success:
            return response.overlays
        return []
    except Exception as e:
        logger.debug("Real overlay fetch failed for doc=%s user=%s: %s", doc.vault_id, user_id, e)
        return []


def _build_overlay_progress(doc, real_overlays: list | None = None) -> dict:
    """Build overlay progress items for the DC right panel.

    Reads REAL overlays from the user's cloud only. No DB fallback.
    If no real overlays exist, returns processing_incomplete status.
    """
    if real_overlays:
        return _build_progress_from_real(doc, real_overlays)
    return {
        "status": "processing_incomplete",
        "message": "Document is vaulted but not yet processed. Overlays pending.",
        "has_data": False,
        "overall_pct": 0,
        "overlays": [],
        "overlay_count": 0,
        "overlay_source": "none",
    }


def _build_progress_from_real(doc, real_overlays: list) -> dict:
    """Map real UnifiedOverlay objects to the DC's 6 progress items.

    Reads ONLY from real overlay payloads in the user's cloud. No DB extracted
    content is used as fallback. If an overlay type is missing, that progress
    item shows as incomplete.
    """
    by_type: dict = {}
    for ov in real_overlays:
        try:
            t = ov.overlay_type.value if hasattr(ov.overlay_type, 'value') else str(ov.overlay_type)
        except Exception:
            t = str(ov.overlay_type)
        by_type.setdefault(t, []).append(ov)

    items: list[dict] = []

    # 1. Certified Upload
    manifest_ovs = by_type.get(OverlayType.VAULT_UPLOAD_MANIFEST.value, [])
    certified = doc.registry_id is not None or bool(manifest_ovs)
    cert_detail = doc.registry_id or (manifest_ovs[0].overlay_id if manifest_ovs else None)
    items.append({
        "name": "Certified Upload",
        "overlay_type": "upload_notarization",
        "icon": "✅" if certified else "⬜",
        "pct": 100 if certified else 0,
        "goal": "Document stored with tamper-proof certificate",
        "detail": cert_detail,
        "items": [cert_detail] if cert_detail else [],
    })

    # 2. Document Type
    class_ovs = by_type.get(OverlayType.DOCUMENT_CLASSIFICATION.value, [])
    typed = bool(class_ovs) or bool(doc.document_type and doc.document_type != "document")
    type_label = None
    if class_ovs:
        payload = class_ovs[0].payload or {}
        type_label = payload.get("document_type", "").replace("_", " ").title() if payload.get("document_type") else None
    if not type_label and doc.document_type and doc.document_type != "document":
        type_label = doc.document_type.replace("_", " ").title()
    items.append({
        "name": "Document Type",
        "overlay_type": "document_classification",
        "icon": "✅" if typed else "⬜",
        "pct": 100 if typed else 0,
        "goal": "Document type identified and confirmed",
        "detail": type_label,
        "items": [type_label] if type_label else [],
    })

    # 3. Text Extraction
    extraction_ovs = by_type.get(OverlayType.DOCUMENT_EXTRACTION.value, [])
    raw_text = ""
    if extraction_ovs:
        for ov in extraction_ovs:
            payload = ov.payload or {}
            raw_text = str(payload.get("text") or payload.get("ocr_text") or payload.get("summary") or "")
            if raw_text:
                break
    has_text = bool(raw_text)
    ocr_pct = 100 if has_text else 0
    text_excerpt = (raw_text[:200] + "…") if len(raw_text) > 200 else raw_text
    items.append({
        "name": "Text Extraction",
        "overlay_type": "ocr_result",
        "icon": "✅" if ocr_pct == 100 else ("🔄" if ocr_pct else "⬜"),
        "pct": ocr_pct,
        "goal": "All text extracted from the document",
        "detail": f"{len(raw_text):,} chars" if has_text else None,
        "items": [text_excerpt] if has_text else [],
    })

    # 4. Dates
    dates: list = []
    if extraction_ovs:
        for ov in extraction_ovs:
            payload = ov.payload or {}
            d = payload.get("dates") or []
            if d:
                dates = d
                break
    if not dates:
        timeline_ovs = by_type.get(OverlayType.TIMELINE_EXTRACTION.value, [])
        for ov in timeline_ovs:
            payload = ov.payload or {}
            d = payload.get("dates") or payload.get("events") or []
            if d:
                dates = d
                break
    n_dates = len(dates)
    dates_pct = min(100, n_dates * 33) if n_dates else 0
    items.append({
        "name": "Dates",
        "overlay_type": "key_date_extraction",
        "icon": "✅" if n_dates >= 2 else ("🔄" if n_dates else "⬜"),
        "pct": dates_pct,
        "goal": "Key dates identified (lease start, end, notice deadlines, etc.)",
        "detail": f"{n_dates} found" if n_dates else None,
        "items": [str(d) for d in dates[:10]],
    })

    # 5. Parties
    party_ovs = by_type.get(OverlayType.PARTY_EXTRACTION.value, [])
    parties: list = []
    if party_ovs:
        for ov in party_ovs:
            payload = ov.payload or {}
            p = payload.get("parties") or []
            if p:
                parties = p
                break
    if not parties:
        parties = []
    n_parties = len(parties)
    parties_pct = min(100, n_parties * 50) if n_parties else 0
    items.append({
        "name": "Parties",
        "overlay_type": "party_extraction",
        "icon": "✅" if n_parties >= 2 else ("🔄" if n_parties else "⬜"),
        "pct": parties_pct,
        "goal": "All parties identified (landlord, tenant, attorney)",
        "detail": f"{n_parties} found" if n_parties else None,
        "items": [str(p) for p in parties[:10]],
    })

    # 6. Amounts
    amounts: list = []
    if extraction_ovs:
        for ov in extraction_ovs:
            payload = ov.payload or {}
            a = payload.get("amounts") or []
            if a:
                amounts = a
                break
    if not amounts:
        amounts = []
    n_amounts = len(amounts)
    items.append({
        "name": "Amounts",
        "overlay_type": "amount_extraction",
        "icon": "✅" if n_amounts else "⬜",
        "pct": 100 if n_amounts else 0,
        "goal": "Rent, deposit, and fee amounts confirmed",
        "detail": f"{n_amounts} found" if n_amounts else None,
        "items": [str(a) for a in amounts[:10]],
    })

    overall_pct = sum(it["pct"] for it in items) // len(items) if items else 0
    has_data = certified or bool(real_overlays)

    return {
        "has_data": has_data,
        "overall_pct": overall_pct,
        "overlays": items,
        "overlay_count": len(real_overlays),
        "overlay_source": "real",
    }


@router.get("/list")
async def dc_list_documents(request: Request) -> JSONResponse:
    """List vault documents with overlay status for the DC left panel.

    Returns documents with id, filename, uploaded_at, document_type,
    overlay_count (null — real count requires per-doc cloud fetch via
    /api/dc/document/{vault_id}/overlays), and verification_status.
    """
    user_id = _auth(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "not_authenticated"})

    documents: list[dict] = []
    try:
        from app.services.vault_upload_service import get_vault_service
        vault_service = get_vault_service()
        vault_docs = await vault_service.get_user_documents(user_id)
        for doc in vault_docs:
            uploaded_raw = doc.uploaded_at
            if isinstance(uploaded_raw, str):
                uploaded_str = uploaded_raw
            elif hasattr(uploaded_raw, "isoformat"):
                uploaded_str = uploaded_raw.isoformat()
            else:
                uploaded_str = str(uploaded_raw)

            # overlay_count is null in list view — real count requires per-doc
            # cloud fetch via /api/dc/document/{vault_id}/overlays.
            verification_status = "verified" if doc.registry_id else ("review" if doc.processed else "new")

            documents.append({
                "id": doc.vault_id,
                "filename": doc.filename,
                "uploaded_at": uploaded_str,
                "document_type": doc.document_type or "",
                "overlay_count": None,
                "verification_status": verification_status,
            })
    except Exception as vault_err:
        logger.warning("DC list: vault fetch failed for user=%s: %s", user_id, vault_err)

    return JSONResponse({
        "documents": documents,
        "total": len(documents),
        "generated_at": utc_now().isoformat(),
    })


def _compute_unlocks(docs: list) -> list[dict]:
    """Compute unlock states for DC feature modules from all user documents.

    Uses ONLY DB index flags (processed, registry_id, document_type) — never reads
    extracted user content from the database. This is compliant with the stateless
    mandate: no user data is read from our PostgreSQL to compute unlocks.

    Rules:
    - Timeline:        1 doc with processed=True and document_type set
    - Journal:         2+ docs with processed=True
    - Contact Manager: any doc with processed=True and document_type set
    - Case Builder:    3+ docs with processed=True and registry_id set
    """
    processed_docs = sum(1 for d in docs if d.processed)
    typed_docs = sum(1 for d in docs if d.processed and d.document_type and d.document_type != "document")
    certified_docs = sum(1 for d in docs if d.processed and d.registry_id)

    return [
        {
            "name": "Timeline",
            "icon": "📅",
            "threshold": "1 processed doc with type identified",
            "unlocked": typed_docs >= 1,
            "progress": f"{typed_docs}/1 docs meet threshold",
        },
        {
            "name": "Journal",
            "icon": "📓",
            "threshold": "2+ processed docs",
            "unlocked": processed_docs >= 2,
            "progress": f"{processed_docs}/2 docs meet threshold",
        },
        {
            "name": "Contact Manager",
            "icon": "👤",
            "threshold": "1 processed doc with type identified",
            "unlocked": typed_docs >= 1,
            "progress": f"{typed_docs}/1 docs meet threshold",
        },
        {
            "name": "Case Builder",
            "icon": "⚖️",
            "threshold": "3+ processed docs with certificate",
            "unlocked": certified_docs >= 3,
            "progress": f"{certified_docs}/3 docs meet threshold",
        },
    ]


@router.get("/unlocks")
async def dc_get_unlocks(request: Request) -> JSONResponse:
    """Compute unlock states for DC feature modules across all user documents.

    Uses ONLY DB index flags (processed, registry_id, document_type) — no cloud I/O,
    no extracted content reads. See _compute_unlocks for threshold rules.
    """
    user_id = _auth(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "not_authenticated"})

    try:
        from app.services.vault_upload_service import get_vault_service
        vault_service = get_vault_service()
        docs = await vault_service.get_user_documents(user_id)
        unlocks = _compute_unlocks(docs)
        return JSONResponse({
            "unlocks": unlocks,
            "doc_count": len(docs),
            "generated_at": utc_now().isoformat(),
        })
    except Exception as e:
        logger.error("DC unlocks error user=%s: %s", user_id, e, exc_info=True)
        return JSONResponse(status_code=500, content={"error": "unlocks_failed", "detail": str(e)})


@router.get("/document/{vault_id}/overlays")
async def dc_get_overlays(vault_id: str, request: Request) -> JSONResponse:
    """Get overlay progress data for the DC right panel.

    Reads REAL overlays from UnifiedOverlayManager in the user's cloud storage.
    No DB fallback. If no overlays exist or cloud is unavailable, returns
    status='processing_incomplete' — the frontend shows a 'try again' message.
    """
    user_id = _auth(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "not_authenticated"})

    try:
        from app.services.vault_upload_service import get_vault_service
        vault_service = get_vault_service()

        doc = await vault_service.get_document(vault_id)
        if not doc:
            return JSONResponse(status_code=404, content={"error": "document_not_found"})
        if doc.user_id != user_id:
            return JSONResponse(status_code=403, content={"error": "access_denied"})

        real_overlays = await _fetch_real_overlays(doc, user_id)
        result = _build_overlay_progress(doc, real_overlays)
        result["vault_id"] = vault_id
        result["generated_at"] = utc_now().isoformat()
        return JSONResponse(result)

    except Exception as e:
        logger.error("DC overlays error vault_id=%s user=%s: %s", vault_id, user_id, e, exc_info=True)
        return JSONResponse(status_code=500, content={"error": "overlays_failed", "detail": str(e)})


@router.get("/document/{vault_id}/view")
async def dc_view_document(vault_id: str, request: Request):
    """Stream a vault document inline for the DC viewer iframe.

    Returns file bytes with Content-Disposition: inline so the browser
    renders it directly (built-in PDF viewer, image renderer, etc.).
    Uses cookie auth — the iframe is same-origin so cookies are sent automatically.
    """
    from fastapi.responses import Response

    user_id = _auth(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "not_authenticated"})

    try:
        from app.services.vault_upload_service import get_vault_service
        vault_service = get_vault_service()

        doc = await vault_service.get_document(vault_id)
        if not doc:
            return JSONResponse(status_code=404, content={"error": "document_not_found"})
        if doc.user_id != user_id:
            return JSONResponse(status_code=403, content={"error": "access_denied"})

        access_token: str | None = None
        if doc.storage_provider != "local":
            from app.core.oauth_token_manager import get_valid_token_for_user
            access_token = get_valid_token_for_user(user_id)
            if not access_token:
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "storage_unavailable",
                        "detail": "No valid storage token — please reconnect your vault storage.",
                    },
                )

        content = await vault_service.get_document_content(vault_id, access_token)
        if not content:
            return JSONResponse(status_code=404, content={"error": "document_content_unavailable"})

        mime = doc.mime_type or "application/octet-stream"
        safe_name = doc.filename.replace('"', "").replace("\\", "")

        return Response(
            content=content,
            media_type=mime,
            headers={
                "Content-Disposition": f'inline; filename="{safe_name}"',
                "Cache-Control": "private, max-age=3600",
                "X-DC-Vault-Id": vault_id,
            },
        )
    except Exception as e:
        logger.error("DC view error vault_id=%s user=%s: %s", vault_id, user_id, e, exc_info=True)
        return JSONResponse(status_code=500, content={"error": "view_failed", "detail": str(e)})


@router.post("/document/{vault_id}/type")
async def dc_set_document_type(vault_id: str, request: Request) -> JSONResponse:
    """Set or correct the document type from the DC viewer dropdown.

    Body: {"document_type": "lease"}  — empty string clears the type.
    Validates against ALLOWED_DOCUMENT_TYPES.
    Writes to DB immediately; also attempts to create a DOCUMENT_CLASSIFICATION
    overlay in cloud storage if the user's OAuth token is available.
    Returns the updated overlay snapshot so the frontend can refresh
    the right panel in one round-trip.
    """
    user_id = _auth(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "not_authenticated"})

    try:
        body = await request.json()
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": "invalid_json", "detail": str(e)})

    document_type = str(body.get("document_type", "")).strip()
    if document_type and document_type not in ALLOWED_DOCUMENT_TYPES:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_document_type",
                "received": document_type,
                "allowed": sorted(ALLOWED_DOCUMENT_TYPES),
            },
        )

    try:
        from app.services.vault_upload_service import get_vault_service
        vault_service = get_vault_service()

        doc = await vault_service.get_document(vault_id)
        if not doc:
            return JSONResponse(status_code=404, content={"error": "document_not_found"})
        if doc.user_id != user_id:
            return JSONResponse(status_code=403, content={"error": "access_denied"})

        # Best-effort OAuth token for overlay creation — DB update succeeds regardless
        access_token: str | None = None
        if doc.storage_provider != "local":
            from app.core.oauth_token_manager import get_valid_token_for_user
            access_token = get_valid_token_for_user(user_id)

        if document_type:
            updated_doc = await vault_service.update_document_type(
                vault_id,
                document_type,
                access_token=access_token,
                storage_provider=doc.storage_provider,
            )
        else:
            # Clear the type — write None directly; no classification overlay needed
            updated_doc = await vault_service.index.update(vault_id, document_type=None)

        if not updated_doc:
            return JSONResponse(status_code=500, content={"error": "update_failed"})

        # After type update, re-fetch real overlays to reflect the new DOCUMENT_CLASSIFICATION
        real_overlays = await _fetch_real_overlays(updated_doc, user_id)
        overlay_snapshot = _build_overlay_progress(updated_doc, real_overlays)

        logger.info(
            "DC set_type: vault_id=%s type=%r user=%s provider=%s token=%s",
            vault_id, document_type or "(cleared)", user_id,
            doc.storage_provider, "yes" if access_token else "no",
        )

        return JSONResponse({
            "ok": True,
            "vault_id": vault_id,
            "document_type": document_type or None,
            "overlays": overlay_snapshot,
        })

    except Exception as e:
        logger.error("DC set_type error vault_id=%s user=%s: %s", vault_id, user_id, e, exc_info=True)
        return JSONResponse(status_code=500, content={"error": "set_type_failed", "detail": str(e)})
