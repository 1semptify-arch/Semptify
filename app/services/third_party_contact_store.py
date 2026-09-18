"""Third-party contact store — THIRD_PARTY_CONTACT overlays in the tenant's vault.

Third-party contacts (landlords, property managers, agencies, attorneys)
extracted from communication imports persist as overlays anchored to
`document_id="third_party:{user_id}"` at VAULT_CONTACTS_FILE. Legacy
`third_party_contacts` rows migrate on first read: non-destructive,
idempotent via `payload["legacy_id"]`, bounded at 25 rows/call.

Consumers:
- `app.services.intake_service` — upserts extracted contacts
- `app.services.redaction_service` — reads active contacts as the redaction
  allowlist (contact info is protected from redaction)

View contract: functions return SimpleNamespace objects carrying the ORM
attribute surface (id, user_id, case_record_id, entity_type, name, email,
phone, address, source, source_document_id, is_active, created_at,
updated_at).
"""

import logging
from datetime import datetime
from types import SimpleNamespace

from app.core.id_gen import make_id
from app.core.overlay_types import OverlayType
from app.core.utc import utc_now
from app.core.user_context import UserContext, build_context_for_user_id
from app.core.vault_paths import VAULT_CONTACTS_FILE
from app.models.unified_overlay_models import CreateOverlayRequest
from app.services.storage import get_provider
from app.services.unified_overlay_manager import UnifiedOverlayManager, get_unified_overlay_manager

logger = logging.getLogger(__name__)

TPC_FIELDS = (
    "id",
    "case_record_id",
    "entity_type",
    "name",
    "email",
    "phone",
    "address",
    "source",
    "source_document_id",
    "is_active",
)


def _anchor(effective_id: str) -> str:
    return f"third_party:{effective_id}"


async def _get_manager(user: UserContext) -> UnifiedOverlayManager:
    storage = get_provider(user.provider.value, access_token=user.access_token)
    return await get_unified_overlay_manager(storage, user.get_effective_user_id())


def _owns(effective_id: str, overlay) -> bool:
    return overlay.created_by == effective_id


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _view(overlay, effective_id: str) -> SimpleNamespace:
    p = overlay.payload
    return SimpleNamespace(
        id=p.get("id") or overlay.overlay_id,
        user_id=effective_id,
        case_record_id=p.get("case_record_id"),
        entity_type=p.get("entity_type"),
        name=p.get("name"),
        email=p.get("email"),
        phone=p.get("phone"),
        address=p.get("address"),
        source=p.get("source"),
        source_document_id=p.get("source_document_id"),
        is_active=bool(p.get("is_active", True)),
        created_at=_parse_dt(p.get("created_at")) or overlay.created_at,
        updated_at=_parse_dt(p.get("updated_at")) or overlay.updated_at,
    )


async def _list_overlays(user: UserContext) -> list:
    manager = await _get_manager(user)
    effective_id = user.get_effective_user_id()
    response = await manager.get_overlays(document_id=_anchor(effective_id), overlay_type=OverlayType.THIRD_PARTY_CONTACT)
    if not response.success:
        logger.warning("Third-party contact list failed for user %s: %s", user.user_id[:8], response.message)
        return []
    return [o for o in response.overlays if _owns(effective_id, o)]


async def list_active(user: UserContext, case_record_id: str | None = None) -> list[SimpleNamespace]:
    """Active third-party contacts. When case_record_id is given, contacts
    linked to that case come first (matching legacy allowlist ordering)."""
    await migrate_legacy_contacts(user)
    overlays = [o for o in await _list_overlays(user) if o.payload.get("is_active", True)]
    views = [_view(o, user.get_effective_user_id()) for o in overlays]
    if case_record_id:
        linked = [v for v in views if v.case_record_id == case_record_id]
        rest = [v for v in views if v.case_record_id != case_record_id]
        return linked + rest
    return views


async def list_active_for_user_id(user_id: str, case_record_id: str | None = None) -> list[SimpleNamespace]:
    """user_id-only reader for redaction_service's allowlist."""
    try:
        user = await build_context_for_user_id(user_id)
    except Exception:
        return []
    return await list_active(user, case_record_id=case_record_id)


async def upsert_contact(
    user: UserContext,
    name: str,
    email: str | None,
    phone: str | None,
    entity_type: str,
    source: str,
    case_record_id: str | None = None,
    source_document_id: str | None = None,
) -> SimpleNamespace:
    """Upsert by email or phone among active contacts — enriches empty name
    on match, creates otherwise. Mirrors the legacy ThirdPartyContact upsert."""
    effective_id = user.get_effective_user_id()
    overlays = await _list_overlays(user)

    existing = None
    if email:
        existing = next(
            (o for o in overlays if o.payload.get("email") == email and o.payload.get("is_active", True)), None
        )
    if existing is None and phone:
        existing = next(
            (o for o in overlays if o.payload.get("phone") == phone and o.payload.get("is_active", True)), None
        )

    if existing is not None:
        if not existing.payload.get("name") and name:
            existing.payload["name"] = name
        existing.payload["updated_at"] = utc_now().isoformat()
        manager = await _get_manager(user)
        await manager.update_overlay(existing.overlay_id, payload=existing.payload)
        return _view(existing, effective_id)

    manager = await _get_manager(user)
    contact_id = make_id("tpc")
    now = utc_now().isoformat()
    response = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.THIRD_PARTY_CONTACT,
            document_id=_anchor(effective_id),
            vault_path=VAULT_CONTACTS_FILE,
            payload={
                "id": contact_id,
                "case_record_id": case_record_id,
                "entity_type": entity_type,
                "name": name,
                "email": email,
                "phone": phone,
                "address": None,
                "source": source,
                "source_document_id": source_document_id,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
            metadata={"entity_type": entity_type, "scope": "third_party_contacts"},
        )
    )
    if not response.success or not response.overlay_id:
        raise RuntimeError(f"Failed to persist third-party contact: {response.message}")
    overlay = await manager.get_overlay(response.overlay_id)
    return _view(overlay, effective_id)


async def migrate_legacy_contacts(user: UserContext, limit: int = 25) -> int:
    """Bounded import of legacy `third_party_contacts` rows. Non-destructive,
    idempotent via payload["legacy_id"]."""
    try:
        from sqlalchemy import select

        from app.core.database import get_db_session
        from app.models.models import ThirdPartyContact
    except Exception:
        return 0

    effective_id = user.get_effective_user_id()
    imported = 0
    try:
        overlays = await _list_overlays(user)
        migrated = {o.payload.get("legacy_id") for o in overlays if o.payload.get("legacy_id")}
        manager = await _get_manager(user)

        async with get_db_session() as db:
            result = await db.execute(
                select(ThirdPartyContact).where(ThirdPartyContact.user_id == user.user_id).limit(limit)
            )
            for row in result.scalars().all():
                if imported >= limit or row.id in migrated:
                    continue
                await manager.create_overlay(
                    CreateOverlayRequest(
                        overlay_type=OverlayType.THIRD_PARTY_CONTACT,
                        document_id=_anchor(effective_id),
                        vault_path=VAULT_CONTACTS_FILE,
                        payload={
                            "id": row.id,
                            "case_record_id": row.case_record_id,
                            "entity_type": row.entity_type,
                            "name": row.name,
                            "email": row.email,
                            "phone": row.phone,
                            "address": row.address,
                            "source": row.source,
                            "source_document_id": row.source_document_id,
                            "is_active": bool(row.is_active),
                            "created_at": row.created_at.isoformat() if row.created_at else None,
                            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                            "legacy_id": row.id,
                            "migrated_from": "third_party_contacts",
                        },
                        metadata={"entity_type": row.entity_type, "scope": "third_party_contacts"},
                    )
                )
                migrated.add(row.id)
                imported += 1
    except Exception:
        logger.exception("Legacy third-party contact migration failed for user %s", user.user_id[:8])
        return imported

    return imported
