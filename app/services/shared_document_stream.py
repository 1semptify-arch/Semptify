"""Shared document streaming — read-only byte delivery for token-gated shares.

Extracted from app.modules.document_center.router so both DOCUMENT_SHARE
recipients and CASE_SHARE reviewers stream vault documents through one path.
Originals are immutable: this module only reads. The caller is responsible
for share/token scope checks before streaming.
"""

import logging

from fastapi.responses import JSONResponse, Response

logger = logging.getLogger(__name__)


async def stream_vault_document(vault_id: str, download: bool = False):
    """Stream an immutable vault document's content.

    Resolves document metadata via the vault index, obtains the owner's
    storage token for non-local providers, and returns the bytes with
    inline/attachment disposition. Never writes — read path only.

    Returns a Response (bytes) or a JSONResponse error the caller returns
    as-is.
    """
    from app.core.auto_refresh import ensure_valid_token
    from app.core.database import get_db_session
    from app.services.vault_upload_service import get_vault_service

    vault_service = get_vault_service()
    doc = await vault_service.get_document(vault_id)
    if not doc:
        return JSONResponse(status_code=404, content={"error": "document_not_found"})

    access_token: str | None = None
    if doc.storage_provider != "local":
        async with get_db_session() as db:
            _, token_obj, _ = await ensure_valid_token(doc.user_id, db)
            access_token = token_obj.access_token if token_obj else None
        if not access_token:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "storage_unavailable",
                    "detail": "The document owner must reconnect storage for this share to work.",
                },
            )

    content = await vault_service.get_document_content(vault_id, access_token)
    if not content:
        return JSONResponse(status_code=404, content={"error": "document_content_unavailable"})

    mime = doc.mime_type or "application/octet-stream"
    safe_name = doc.filename.replace('"', "").replace("\\", "")
    disposition = "attachment" if download else "inline"
    headers = {"Content-Disposition": f'{disposition}; filename="{safe_name}"'}
    return Response(content=content, media_type=mime, headers=headers)
