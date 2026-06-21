"""
External Document Client — Phase 3.2a

Read documents on behalf of an external module. Enforces document.read
permission. Write requires document.write (rarely granted to external modules).
"""
import logging
from typing import List, Optional

from app.sdk.external.context import ExternalModuleContext
from app.sdk.external.permissions import Permission

logger = logging.getLogger(__name__)


class DocumentClient:
    """External module document access — enforces least privilege."""

    def __init__(self, ctx: ExternalModuleContext):
        self._ctx = ctx

    async def list_documents(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        """List documents. Requires document.read."""
        self._ctx.require_permission(Permission.DOCUMENT_READ.value, "list_documents")
        target_user = user_id or self._ctx.user_id
        logger.info(
            "ExternalDocument: module=%s list_documents user=%s",
            self._ctx.module_name, target_user[:6] + "...",
        )
        # Delegate to internal document service
        from app.modules.documents.service import list_documents
        return await list_documents(
            user_id=target_user,
            limit=limit,
            offset=offset,
        )

    async def read_document(self, document_id: str) -> dict:
        """Read a document's metadata and content. Requires document.read."""
        self._ctx.require_permission(Permission.DOCUMENT_READ.value, "read_document")
        logger.info(
            "ExternalDocument: module=%s read_document id=%s",
            self._ctx.module_name, document_id,
        )
        from app.modules.documents.service import get_document
        return await get_document(document_id=document_id)

    async def upload_document(
        self,
        filename: str,
        content: bytes,
        metadata: Optional[dict] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """Upload a document. Requires document.write."""
        self._ctx.require_permission(Permission.DOCUMENT_WRITE.value, "upload_document")
        target_user = user_id or self._ctx.user_id
        logger.info(
            "ExternalDocument: module=%s upload_document name=%s size=%d",
            self._ctx.module_name, filename, len(content),
        )
        from app.modules.documents.service import upload_document
        return await upload_document(
            user_id=target_user,
            filename=filename,
            content=content,
            metadata=metadata or {},
            source=f"external:{self._ctx.module_name}",
        )
