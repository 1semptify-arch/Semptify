"""OCR-first intake API — mounted at /api/dc/intake.

Endpoints
---------
POST /start                  — begin an intake session for an uploaded vault doc
GET  /{session_id}           — session state: proposals + answers so far
POST /{session_id}/answer    — record one review answer (yes | no | edit)
POST /{session_id}/finalize  — write reviewed fields + state into vault.db

The session is ephemeral in-memory (ADR-0007 server fallback is memory-only);
the documents row lands in vault.db at start (unverified) and the reviewed
fields land at finalize. Every proposed field must be answered — nothing is
written silently.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.auto_refresh import ensure_valid_token
from app.core.cookie_auth import verify_user_id
from app.core.database import get_db_session
from app.core.user_id import COOKIE_USER_ID
from app.sdk.vault.db import VaultDbError
from app.services import intake_ocr
from app.services.storage import get_provider

logger = logging.getLogger(__name__)

router = APIRouter()


class StartBody(BaseModel):
    vault_id: str


class AnswerBody(BaseModel):
    field_id: str
    answer: str  # yes | no | edit
    value: str | None = None


class FinalizeBody(BaseModel):
    doc_type: str | None = None  # optional user-corrected doc type


def _auth(request: Request) -> str | None:
    cookie_value = request.cookies.get(COOKIE_USER_ID)
    if not cookie_value:
        return None
    return verify_user_id(cookie_value)


async def _storage_for(user_id: str, doc):
    """Provider handle for the doc's storage tier, or None when unavailable."""
    if not doc or doc.storage_provider == "local":
        return None
    async with get_db_session() as db:
        _, token_obj, _ = await ensure_valid_token(user_id, db)
    if not token_obj or not token_obj.access_token:
        return None
    return get_provider(doc.storage_provider, access_token=token_obj.access_token)


def _owned_session(session_id: str, user_id: str):
    session = intake_ocr.get_session(session_id)
    if session is None:
        return None, JSONResponse(status_code=404, content={"error": "session_not_found"})
    if session.user_id != user_id:
        return None, JSONResponse(status_code=403, content={"error": "forbidden"})
    return session, None


@router.post("/start")
async def intake_start(body: StartBody, request: Request) -> JSONResponse:
    """Extract -> unverified documents row -> confirm-loop session."""
    user_id = _auth(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "not_authenticated"})

    from app.services.vault_upload_service import get_vault_service

    vault_service = get_vault_service()
    doc = await vault_service.get_document(body.vault_id)
    if doc is None or doc.user_id != user_id:
        return JSONResponse(status_code=404, content={"error": "document_not_found"})

    storage = await _storage_for(user_id, doc)
    if storage is None:
        return JSONResponse(
            status_code=409,
            content={
                "error": "vault_unavailable",
                "detail": "Document lives outside a connected cloud vault — intake needs the provisioned vault.",
            },
        )

    access_token = None
    async with get_db_session() as db:
        _, token_obj, _ = await ensure_valid_token(user_id, db)
        access_token = token_obj.access_token if token_obj else None
    content = await vault_service.get_document_content(body.vault_id, access_token=access_token)
    if content is None:
        return JSONResponse(status_code=422, content={"error": "content_unavailable"})

    try:
        session = await intake_ocr.start_intake(
            user_id=user_id,
            vault_id=doc.vault_id,
            filename=doc.filename,
            storage_ref=doc.storage_path,
            content=content,
            storage=storage,
        )
    except VaultDbError as exc:
        return JSONResponse(
            status_code=409,
            content={"error": "vault_db_missing", "detail": str(exc)},
        )
    return JSONResponse(session.to_dict())


@router.get("/{session_id}")
async def intake_state(session_id: str, request: Request) -> JSONResponse:
    user_id = _auth(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "not_authenticated"})
    session, err = _owned_session(session_id, user_id)
    if err:
        return err
    return JSONResponse(session.to_dict())


@router.post("/{session_id}/answer")
async def intake_answer(session_id: str, body: AnswerBody, request: Request) -> JSONResponse:
    user_id = _auth(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "not_authenticated"})
    session, err = _owned_session(session_id, user_id)
    if err:
        return err
    try:
        updated = intake_ocr.answer_field(session, body.field_id, body.answer, body.value)
    except KeyError:
        return JSONResponse(status_code=404, content={"error": "field_not_found"})
    except ValueError as exc:
        return JSONResponse(status_code=422, content={"error": str(exc)})
    return JSONResponse(
        {
            "success": True,
            "field": updated.to_dict(),
            "fields_answered": sum(1 for f in session.fields if f.answer),
            "fields_total": len(session.fields),
        }
    )


@router.post("/{session_id}/finalize")
async def intake_finalize(session_id: str, body: FinalizeBody, request: Request) -> JSONResponse:
    """All fields answered -> single vault.db write of fields + state."""
    user_id = _auth(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "not_authenticated"})
    session, err = _owned_session(session_id, user_id)
    if err:
        return err

    from app.services.vault_upload_service import get_vault_service

    doc = await get_vault_service().get_document(session.vault_id)
    storage = await _storage_for(user_id, doc)
    if storage is None:
        return JSONResponse(status_code=409, content={"error": "vault_unavailable"})
    try:
        result = await intake_ocr.finalize(session, storage, doc_type=body.doc_type)
    except VaultDbError as exc:
        return JSONResponse(status_code=409, content={"error": "vault_db_missing", "detail": str(exc)})
    if result.get("success"):
        await _sync_doc_index(session, body.doc_type, result)
    status = 200 if result.get("success") else 422
    return JSONResponse(status_code=status, content=result)


async def _sync_doc_index(session, doc_type_override: str | None, result: dict) -> None:
    """Mirror the finalized review onto the server-side doc index.

    vault.db owns the reviewed fields; the index record carries the
    summary (document_type, processed flag, review_state_json) that the
    document list, checklist, and status filter read. Failures here are
    logged, never raised — the vault write already succeeded.
    """
    try:
        from app.services.vault_upload_service import get_vault_service

        vault_service = get_vault_service()
        doc = await vault_service.get_document(session.vault_id)
        try:
            review_state = json.loads((doc.review_state_json if doc else None) or "{}")
        except Exception:
            review_state = {}
        field_state = review_state.get("field_confirm_state", {})
        for f in session.fields:
            if f.answer == "yes":
                field_state[f.name] = "confirmed"
            elif f.answer == "edit":
                field_state[f.name] = "corrected"
                field_state[f.name + "_value"] = f.final_value
            elif f.answer == "no":
                field_state[f.name] = "rejected"
        review_state["field_confirm_state"] = field_state
        manual = {
            "verified": "verified",
            "in_review": "review",
            "mismatched": "mismatched",
        }.get(result.get("verification_state"))
        if manual:
            review_state["manual_status"] = manual
        await vault_service.index.update(
            session.vault_id,
            document_type=doc_type_override or session.doc_type,
            processed=True,
            review_state_json=json.dumps(review_state),
        )
    except Exception:
        logger.warning("intake finalize index sync failed for %s", session.vault_id)
