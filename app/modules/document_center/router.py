"""Document Center API — DC-specific endpoints for the 3-pane viewer.

Lifecycle: dev_only (admin-only while Slices 1-7 are under construction).

Endpoints
---------
GET  /api/dc/list                      — vault docs with overlay status for left pane
POST /api/dc/document/{doc_id}/type    — set/correct document type from viewer dropdown
"""
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.cookie_auth import verify_user_id
from app.core.user_id import COOKIE_USER_ID
from app.core.utc import utc_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dc", tags=["Document Center"])

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


@router.get("/list")
async def dc_list_documents(request: Request) -> JSONResponse:
    """List vault documents with overlay status for the DC left panel.

    Returns documents with id, filename, uploaded_at, document_type,
    overlay_count (0 until Slice 4), and verification_status ('new' until Slice 4).
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

            documents.append({
                "id": doc.vault_id,
                "filename": doc.filename,
                "uploaded_at": uploaded_str,
                "document_type": doc.document_type or "",
                "overlay_count": 0,
                "verification_status": "new",
            })
    except Exception as vault_err:
        logger.warning("DC list: vault fetch failed for user=%s: %s", user_id, vault_err)

    return JSONResponse({
        "documents": documents,
        "total": len(documents),
        "generated_at": utc_now().isoformat(),
    })


def _synthesize_overlays(doc) -> dict:
    """Build overlay progress items from VaultDocument metadata stored in the DB.

    No cloud storage I/O — all data is already local (processed, extracted_data, etc.).
    Returns the structure expected by the DC right panel.
    """
    extracted: dict = doc.extracted_data or {}
    items: list[dict] = []

    # 1. Certified upload
    certified = doc.registry_id is not None
    items.append({
        "name": "Certified Upload",
        "overlay_type": "upload_notarization",
        "icon": "✅" if certified else "⬜",
        "pct": 100 if certified else 0,
        "goal": "Document stored with tamper-proof certificate",
        "detail": doc.registry_id if certified else None,
    })

    # 2. Document type identified
    typed = bool(doc.document_type and doc.document_type != "document")
    items.append({
        "name": "Document Type",
        "overlay_type": "document_classification",
        "icon": "✅" if typed else "⬜",
        "pct": 100 if typed else 0,
        "goal": "Document type identified and confirmed",
        "detail": doc.document_type.replace("_", " ").title() if typed else None,
    })

    # 3. Text extraction (OCR)
    raw_text: str = str(extracted.get("text") or extracted.get("ocr_text") or "")
    has_text = bool(raw_text)
    ocr_pct = 100 if (doc.processed and has_text) else (50 if doc.processed else 0)
    items.append({
        "name": "Text Extraction",
        "overlay_type": "ocr_result",
        "icon": "✅" if ocr_pct == 100 else ("🔄" if ocr_pct else "⬜"),
        "pct": ocr_pct,
        "goal": "All text extracted from the document",
        "detail": f"{len(raw_text):,} chars" if has_text else None,
    })

    # 4. Dates
    dates: list = extracted.get("dates") or []
    n_dates = len(dates)
    dates_pct = min(100, n_dates * 33) if n_dates else (50 if doc.processed else 0)
    items.append({
        "name": "Dates",
        "overlay_type": "key_date_extraction",
        "icon": "✅" if n_dates >= 2 else ("🔄" if n_dates else "⬜"),
        "pct": dates_pct,
        "goal": "Key dates identified (lease start, end, notice deadlines, etc.)",
        "detail": f"{n_dates} found" if n_dates else None,
    })

    # 5. Parties
    parties: list = extracted.get("parties") or []
    n_parties = len(parties)
    parties_pct = min(100, n_parties * 50) if n_parties else (50 if doc.processed else 0)
    items.append({
        "name": "Parties",
        "overlay_type": "party_extraction",
        "icon": "✅" if n_parties >= 2 else ("🔄" if n_parties else "⬜"),
        "pct": parties_pct,
        "goal": "All parties identified (landlord, tenant, attorney)",
        "detail": f"{n_parties} found" if n_parties else None,
    })

    # 6. Amounts
    amounts: list = extracted.get("amounts") or []
    n_amounts = len(amounts)
    items.append({
        "name": "Amounts",
        "overlay_type": "amount_extraction",
        "icon": "✅" if n_amounts else "⬜",
        "pct": 100 if n_amounts else (50 if doc.processed else 0),
        "goal": "Rent, deposit, and fee amounts confirmed",
        "detail": f"{n_amounts} found" if n_amounts else None,
    })

    overall_pct = sum(it["pct"] for it in items) // len(items) if items else 0
    has_data = certified or doc.processed

    return {
        "has_data": has_data,
        "overall_pct": overall_pct,
        "overlays": items,
    }


def _compute_unlocks(docs: list) -> list[dict]:
    """Compute unlock states for DC feature modules from all user documents.

    Rules:
    - Timeline:        1 doc with avg(Dates pct, Parties pct) >= 80
    - Journal:         2+ docs with overall_pct >= 60
    - Contact Manager: any doc with Parties pct == 100
    - Case Builder:    3+ docs with overall_pct >= 80
    """
    scores = [_synthesize_overlays(doc) for doc in docs]

    def _pct_for(s: dict, overlay_type: str) -> int:
        return next((o["pct"] for o in s["overlays"] if o["overlay_type"] == overlay_type), 0)

    def _dates_parties_avg(s: dict) -> int:
        return (_pct_for(s, "key_date_extraction") + _pct_for(s, "party_extraction")) // 2

    timeline_docs    = sum(1 for s in scores if _dates_parties_avg(s) >= 80)
    verified_60_docs = sum(1 for s in scores if s["overall_pct"] >= 60)
    contact_docs     = sum(1 for s in scores if _pct_for(s, "party_extraction") == 100)
    verified_80_docs = sum(1 for s in scores if s["overall_pct"] >= 80)

    return [
        {
            "name": "Timeline",
            "icon": "📅",
            "threshold": "1 doc with Dates + Parties ≥ 80%",
            "unlocked": timeline_docs >= 1,
            "progress": f"{timeline_docs}/1 docs meet threshold",
        },
        {
            "name": "Journal",
            "icon": "📓",
            "threshold": "2+ docs verified ≥ 60%",
            "unlocked": verified_60_docs >= 2,
            "progress": f"{verified_60_docs}/2 docs meet threshold",
        },
        {
            "name": "Contact Manager",
            "icon": "👤",
            "threshold": "Parties overlay = 100%",
            "unlocked": contact_docs >= 1,
            "progress": f"{contact_docs}/1 docs meet threshold",
        },
        {
            "name": "Case Builder",
            "icon": "⚖️",
            "threshold": "3 docs verified ≥ 80%",
            "unlocked": verified_80_docs >= 3,
            "progress": f"{verified_80_docs}/3 docs meet threshold",
        },
    ]


@router.get("/unlocks")
async def dc_get_unlocks(request: Request) -> JSONResponse:
    """Compute unlock states for DC feature modules across all user documents.

    Iterates every VaultDocument for the user, synthesizes overlay scores in memory
    (no cloud I/O), and checks each unlock threshold.
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

    Synthesizes overlay status from VaultDocument metadata already in the DB.
    No cloud storage I/O required — fast, always available.
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

        result = _synthesize_overlays(doc)
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

        overlay_snapshot = _synthesize_overlays(updated_doc)

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
