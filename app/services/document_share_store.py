"""Document share store — DOCUMENT_SHARE overlays in the owner's cloud vault.

Share grants persist as overlays anchored to `document_id="shares:{user_id}"`
at VAULT_RECORDS_FILE. A share is the owner's data (their grant of access) —
the recipient only ever sees the token-gated view.

Token design: new share tokens are owner-scoped —
`"{effective_user_id}:{urlsafe32}"` — so `/api/dc/shared/{token}` can resolve
the owning vault without any server-side index. owner_user_id was already
returned to recipients in the shared-document response, so embedding it in
the token exposes nothing new.

Legacy `document_shares` rows migrate on the owner's first share listing:
non-destructive, idempotent via `payload["legacy_id"]`, bounded 25 rows/call.
Migrated tokens are rewritten to owner-scoped form (`{owner}:{old_token}`);
bare-token links created before the migration still resolve through a
read-only fallback query against the legacy table until it is dropped.

View contract: SimpleNamespace carrying the ORM surface used by
document_center/router.py (id, owner_user_id, vault_id,
recipient_identifier, scope, message, share_token, expires_at, accessed_at,
access_count, created_at).
"""

import logging
import secrets
from datetime import datetime
from types import SimpleNamespace

from app.core.id_gen import make_id
from app.core.overlay_types import OverlayType
from app.core.utc import utc_now
from app.core.user_context import UserContext, build_context_for_user_id
from app.core.vault_paths import VAULT_RECORDS_FILE
from app.models.unified_overlay_models import CreateOverlayRequest
from app.services.storage import get_provider
from app.services.unified_overlay_manager import UnifiedOverlayManager, get_unified_overlay_manager

logger = logging.getLogger(__name__)


def _anchor(effective_id: str) -> str:
    return f"shares:{effective_id}"


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


def _view(overlay, owner_id: str) -> SimpleNamespace:
    p = overlay.payload
    return SimpleNamespace(
        id=p.get("share_id") or overlay.overlay_id,
        owner_user_id=owner_id,
        vault_id=p.get("vault_id"),
        recipient_identifier=p.get("recipient_identifier"),
        scope=p.get("scope"),
        message=p.get("message"),
        share_token=p.get("share_token"),
        expires_at=_parse_dt(p.get("expires_at")),
        accessed_at=_parse_dt(p.get("accessed_at")),
        access_count=p.get("access_count") or 0,
        created_at=_parse_dt(p.get("created_at")) or overlay.created_at,
        overlay_id=overlay.overlay_id,
        is_legacy_row=False,
    )


async def _list_overlays(user: UserContext) -> list:
    manager = await _get_manager(user)
    effective_id = user.get_effective_user_id()
    response = await manager.get_overlays(document_id=_anchor(effective_id), overlay_type=OverlayType.DOCUMENT_SHARE)
    if not response.success:
        logger.warning("Share overlay list failed for user %s: %s", user.user_id[:8], response.message)
        return []
    return [o for o in response.overlays if o.created_by == effective_id]


async def create_share(
    user: UserContext,
    vault_id: str,
    recipient: str,
    scope: str,
    message: str | None = None,
    expires_at: datetime | None = None,
) -> SimpleNamespace | None:
    """Create an owner-scoped share overlay. Token embeds the effective user id
    so recipients can resolve the owning vault with no server-side index."""
    effective_id = user.get_effective_user_id()
    manager = await _get_manager(user)

    share_token = f"{effective_id}:{secrets.token_urlsafe(32)}"
    payload = {
        "share_id": make_id("share"),
        "vault_id": vault_id,
        "recipient_identifier": recipient,
        "scope": scope,
        "message": message,
        "share_token": share_token,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "accessed_at": None,
        "access_count": 0,
        "created_at": utc_now().isoformat(),
    }
    response = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.DOCUMENT_SHARE,
            document_id=_anchor(effective_id),
            vault_path=VAULT_RECORDS_FILE,
            payload=payload,
            metadata={"scope": scope, "scope_area": "shares"},
        )
    )
    if not response.success or not response.overlay_id:
        logger.error("Failed to create share for user %s: %s", user.user_id[:8], response.message)
        return None
    overlay = await manager.get_overlay(response.overlay_id)
    return _view(overlay, effective_id) if overlay else None


async def list_shares(user: UserContext, vault_id: str | None = None) -> list[SimpleNamespace]:
    """Shares owned by the user (optionally one document). Migrates legacy rows first."""
    await migrate_legacy_shares(user)
    overlays = await _list_overlays(user)
    if vault_id:
        overlays = [o for o in overlays if o.payload.get("vault_id") == vault_id]
    overlays.sort(key=lambda o: o.payload.get("created_at") or "", reverse=True)
    effective_id = user.get_effective_user_id()
    return [_view(o, effective_id) for o in overlays]


async def resolve_share(share_token: str) -> SimpleNamespace | None:
    """Resolve a share token to its record — no user context required.

    Owner-scoped tokens (`owner:token`) read the owner's vault. Bare legacy
    tokens fall back to a read-only query on the legacy table (rows persist
    until the Alembic drop phase)."""
    owner_id, sep, _raw = share_token.rpartition(":")
    if sep and owner_id:
        user = await build_context_for_user_id(owner_id)
        if user:
            effective_id = user.get_effective_user_id()
            for o in await _list_overlays(user):
                if o.payload.get("share_token") == share_token:
                    return _view(o, effective_id)
        return None
    return await _resolve_legacy_token(share_token)


async def record_share_access(share_token: str) -> None:
    """Bump access_count/accessed_at on the share record (vault or legacy row)."""
    owner_id, sep, _raw = share_token.rpartition(":")
    if sep and owner_id:
        user = await build_context_for_user_id(owner_id)
        if not user:
            return
        for o in await _list_overlays(user):
            if o.payload.get("share_token") == share_token:
                o.payload["access_count"] = (o.payload.get("access_count") or 0) + 1
                o.payload["accessed_at"] = utc_now().isoformat()
                manager = await _get_manager(user)
                await manager.update_overlay(o.overlay_id, payload=o.payload)
                return
        return
    await _record_legacy_access(share_token)


def _legacy_view(row) -> SimpleNamespace:
    return SimpleNamespace(
        id=row.id,
        owner_user_id=row.owner_user_id,
        vault_id=row.vault_id,
        recipient_identifier=row.recipient_identifier,
        scope=row.scope,
        message=row.message,
        share_token=row.share_token,
        expires_at=row.expires_at,
        accessed_at=row.accessed_at,
        access_count=row.access_count or 0,
        created_at=row.created_at,
        overlay_id=None,
        is_legacy_row=True,
    )


async def _resolve_legacy_token(share_token: str) -> SimpleNamespace | None:
    """Bare-token resolution for pre-migration share links. Read-mostly: the
    row is migrated to the owner's vault on access so state converges."""
    try:
        from sqlalchemy import select

        from app.core.database import get_db_session
        from app.models.models import DocumentShare
    except Exception:
        return None
    try:
        async with get_db_session() as db:
            result = await db.execute(select(DocumentShare).where(DocumentShare.share_token == share_token))
            row = result.scalar_one_or_none()
            if not row:
                return None
            view = _legacy_view(row)
            # Converge: import this share into the owner's vault so subsequent
            # resolution/metrics use the overlay. Best-effort — failure is fine.
            try:
                user = await build_context_for_user_id(row.owner_user_id)
                if user:
                    await _import_legacy_row(user, row)
            except Exception:
                logger.debug("Legacy share import skipped for %s", row.owner_user_id[:8])
            return view
    except Exception:
        logger.exception("Legacy share token resolution failed")
        return None


async def _record_legacy_access(share_token: str) -> None:
    try:
        from sqlalchemy import select

        from app.core.database import get_db_session
        from app.models.models import DocumentShare
    except Exception:
        return
    try:
        async with get_db_session() as db:
            result = await db.execute(select(DocumentShare).where(DocumentShare.share_token == share_token))
            row = result.scalar_one_or_none()
            if row:
                row.access_count = (row.access_count or 0) + 1
                row.accessed_at = utc_now()
                await db.commit()
    except Exception:
        logger.debug("Legacy share access update failed")


async def _import_legacy_row(user: UserContext, row) -> bool:
    """Import one legacy row, rewriting its token to owner-scoped form."""
    effective_id = user.get_effective_user_id()
    overlays = await _list_overlays(user)
    if any(o.payload.get("legacy_id") == row.id for o in overlays):
        return False
    manager = await _get_manager(user)
    response = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.DOCUMENT_SHARE,
            document_id=_anchor(effective_id),
            vault_path=VAULT_RECORDS_FILE,
            payload={
                "share_id": row.id,
                "vault_id": row.vault_id,
                "recipient_identifier": row.recipient_identifier,
                "scope": row.scope,
                "message": row.message,
                "share_token": f"{effective_id}:{row.share_token}",
                "legacy_token": row.share_token,
                "expires_at": row.expires_at.isoformat() if row.expires_at else None,
                "accessed_at": row.accessed_at.isoformat() if row.accessed_at else None,
                "access_count": row.access_count or 0,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "legacy_id": row.id,
                "migrated_from": "document_shares",
            },
            metadata={"scope": row.scope, "scope_area": "shares"},
        )
    )
    return bool(response.success)


async def migrate_legacy_shares(user: UserContext, limit: int = 25) -> int:
    """Bounded import of legacy `document_shares` rows owned by the user.
    Non-destructive, idempotent via payload["legacy_id"]. Tokens are rewritten
    to owner-scoped form; the bare old token is kept in payload["legacy_token"]
    and still resolves via the legacy-table fallback until the drop phase."""
    try:
        from sqlalchemy import select

        from app.core.database import get_db_session
        from app.models.models import DocumentShare
    except Exception:
        return 0

    imported = 0
    try:
        async with get_db_session() as db:
            result = await db.execute(
                select(DocumentShare)
                .where(DocumentShare.owner_user_id == user.user_id)
                .order_by(DocumentShare.created_at)
                .limit(limit)
            )
            for row in result.scalars().all():
                if imported >= limit:
                    break
                if await _import_legacy_row(user, row):
                    imported += 1
    except Exception:
        logger.exception("Legacy share migration failed for user %s", user.user_id[:8])
        return imported

    return imported
