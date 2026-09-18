"""
Contacts Service
================
Per-user contact store backed by the Unified Overlay System.

Contacts persist as CONTACT overlays and their interaction log as
CONTACT_INTERACTION overlays — both anchored to
document_id="contacts:{user_id}" in the user's own cloud storage
(vault-persistence-migration, Phase 1). Interactions reference their contact
via payload["contact_id"], which accepts the contact's overlay_id or its
legacy payload id so migrated data keeps working. No server-side database
rows: the tenant's records live in the tenant's vault.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select

from app.core.database import get_db_session
from app.core.id_gen import make_id
from app.core.overlay_types import OverlayType
from app.core.user_context import UserContext
from app.core.utc import utc_now
from app.core.vault_paths import VAULT_CONTACTS_FILE
from app.models.models import Contact as ContactModel
from app.models.models import ContactInteraction as ContactInteractionModel
from app.models.unified_overlay_models import CreateOverlayRequest, UnifiedOverlay
from app.services.storage import get_provider
from app.services.unified_overlay_manager import get_unified_overlay_manager

logger = logging.getLogger(__name__)


def get_contacts_anchor_id(user_id: str) -> str:
    """Return the per-user contacts document_id anchor."""
    return f"contacts:{user_id}"


def get_contacts_vault_path() -> str:
    """Return the canonical vault path used as the contacts anchor."""
    return VAULT_CONTACTS_FILE


async def _get_overlay_manager(user: UserContext):
    """Build an overlay manager labelled with the effective user id so
    records created during support impersonation belong to the tenant."""
    storage = get_provider(user.provider.value, access_token=user.access_token)
    return await get_unified_overlay_manager(storage, user.get_effective_user_id())


def _owns(user: UserContext, overlay: UnifiedOverlay, overlay_type: OverlayType) -> bool:
    """True if the overlay is the given type owned by the effective user."""
    return overlay.overlay_type == overlay_type and overlay.created_by == user.get_effective_user_id()


def _owns_id(effective_id: str, overlay: UnifiedOverlay, overlay_type: OverlayType) -> bool:
    return overlay.overlay_type == overlay_type and overlay.created_by == effective_id


def _to_iso(value):
    """Normalize datetimes to ISO strings for the payload; all other JSON-safe
    values (bool, int, str, list, None) pass through unchanged."""
    if isinstance(value, datetime):
        return value.isoformat()
    return value


CONTACT_FIELDS = (
    "contact_type",
    "role",
    "name",
    "organization",
    "title",
    "phone",
    "phone_alt",
    "email",
    "fax",
    "address_line1",
    "address_line2",
    "city",
    "state",
    "zip_code",
    "website",
    "notes",
    "tags",
    "source",
    "source_document_id",
    "last_contact_date",
    "interaction_count",
    "is_active",
    "is_starred",
)


async def create_contact(user: UserContext, **fields) -> UnifiedOverlay:
    """Create a contact overlay in the user's cloud."""
    manager = await _get_overlay_manager(user)
    payload = {k: _to_iso(v) for k, v in fields.items() if k in CONTACT_FIELDS}
    payload.setdefault("source", "manual")
    payload.setdefault("is_active", True)
    payload.setdefault("is_starred", False)
    payload.setdefault("interaction_count", 0)
    payload["id"] = make_id("con")
    response = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.CONTACT,
            document_id=get_contacts_anchor_id(user.get_effective_user_id()),
            vault_path=get_contacts_vault_path(),
            payload=payload,
            metadata={
                "contact_type": payload.get("contact_type"),
                "scope": "contacts",
            },
        )
    )
    if not response.success or not response.overlay_id:
        logger.error("Failed to create contact for user %s: %s", user.user_id[:8], response.message)
        raise RuntimeError(f"Could not save contact: {response.message}")
    overlay = await manager.get_overlay(response.overlay_id)
    if overlay is None:
        raise RuntimeError("Contact was reported as created but cannot be retrieved")
    return overlay


async def list_contacts(
    user: UserContext,
    *,
    contact_type: str | None = None,
    role: str | None = None,
    starred_only: bool = False,
    active_only: bool = True,
    search: str | None = None,
) -> tuple[list[UnifiedOverlay], int]:
    """Return (contacts, total) sorted starred-first then by name."""
    await migrate_legacy_contacts(user)
    manager = await _get_overlay_manager(user)
    response = await manager.get_overlays(
        document_id=get_contacts_anchor_id(user.get_effective_user_id()),
        overlay_type=OverlayType.CONTACT,
    )
    if not response.success:
        logger.error("Failed to list contacts for user %s: %s", user.user_id[:8], response.filters_applied)
        return [], 0

    contacts = [o for o in response.overlays if _owns(user, o, OverlayType.CONTACT)]
    if contact_type:
        contacts = [o for o in contacts if o.payload.get("contact_type") == contact_type]
    if role:
        contacts = [o for o in contacts if o.payload.get("role") == role]
    if starred_only:
        contacts = [o for o in contacts if o.payload.get("is_starred")]
    if active_only:
        contacts = [o for o in contacts if o.payload.get("is_active")]
    if search:
        needle = search.lower()
        contacts = [
            o
            for o in contacts
            if needle in (o.payload.get("name") or "").lower()
            or needle in (o.payload.get("organization") or "").lower()
            or needle in (o.payload.get("email") or "").lower()
        ]
    contacts.sort(key=lambda o: (not o.payload.get("is_starred"), (o.payload.get("name") or "").lower()))
    return contacts, len(contacts)


async def list_contacts_for_user_id(
    user_id: str,
    *,
    contact_type: str | None = None,
    role: str | None = None,
    starred_only: bool = False,
    active_only: bool = True,
    search: str | None = None,
) -> tuple[list[UnifiedOverlay], int]:
    """list_contacts for callers that only have a user_id (public_forms,
    search, document_flow_orchestrator). Returns ([], 0) on context failure."""
    from app.core.user_context import build_context_for_user_id

    context = await build_context_for_user_id(user_id)
    if context is None:
        return [], 0
    return await list_contacts(
        context,
        contact_type=contact_type,
        role=role,
        starred_only=starred_only,
        active_only=active_only,
        search=search,
    )


async def _resolve_contact(manager, user: UserContext, contact_id: str) -> UnifiedOverlay | None:
    """Resolve a contact by overlay id, or by a legacy ``con_`` id carried in
    the overlay payload for migrated rows."""
    overlay = await manager.get_overlay(contact_id)
    if overlay is not None and _owns(user, overlay, OverlayType.CONTACT):
        return overlay

    response = await manager.get_overlays(
        document_id=get_contacts_anchor_id(user.get_effective_user_id()),
        overlay_type=OverlayType.CONTACT,
    )
    if not response.success:
        return None
    for candidate in response.overlays:
        if _owns(user, candidate, OverlayType.CONTACT) and (
            candidate.payload.get("id") == contact_id or candidate.payload.get("legacy_id") == contact_id
        ):
            return candidate
    return None


async def get_contact(user: UserContext, contact_id: str) -> UnifiedOverlay | None:
    """Get a single contact by id, ownership-checked."""
    manager = await _get_overlay_manager(user)
    return await _resolve_contact(manager, user, contact_id)


async def update_contact(user: UserContext, contact_id: str, fields: dict) -> UnifiedOverlay | None:
    """Merge fields into a contact's payload. Returns the updated overlay."""
    manager = await _get_overlay_manager(user)
    overlay = await _resolve_contact(manager, user, contact_id)
    if overlay is None:
        return None

    normalized = {k: _to_iso(v) for k, v in fields.items() if k in CONTACT_FIELDS}
    overlay.payload.update(normalized)
    overlay.payload["updated_at"] = utc_now().isoformat()
    if not await manager.update_overlay(overlay.overlay_id, payload=overlay.payload):
        return None
    return await manager.get_overlay(overlay.overlay_id)


async def delete_contact(user: UserContext, contact_id: str) -> bool:
    """Delete a contact overlay."""
    manager = await _get_overlay_manager(user)
    overlay = await _resolve_contact(manager, user, contact_id)
    if overlay is None:
        return False
    return await manager.delete_overlay(overlay.overlay_id)


def _contact_ids(contact: UnifiedOverlay) -> set[str]:
    """All ids that may reference this contact from interaction payloads."""
    return {
        v
        for v in (contact.overlay_id, contact.payload.get("id"), contact.payload.get("legacy_id"))
        if v
    }


# ---------------------------------------------------------------------------
# Interactions
# ---------------------------------------------------------------------------

INTERACTION_FIELDS = (
    "interaction_type",
    "direction",
    "subject",
    "summary",
    "interaction_date",
    "duration_minutes",
    "related_document_ids",
    "follow_up_needed",
    "follow_up_date",
    "follow_up_notes",
)


async def create_interaction(user: UserContext, contact_id: str, **fields) -> UnifiedOverlay | None:
    """Log an interaction with a contact. Also stamps the contact's
    last_contact_date and increments interaction_count (legacy semantics)."""
    manager = await _get_overlay_manager(user)
    contact = await _resolve_contact(manager, user, contact_id)
    if contact is None:
        return None

    payload = {k: _to_iso(v) for k, v in fields.items() if k in INTERACTION_FIELDS}
    payload["id"] = make_id("con")
    payload["contact_id"] = contact.overlay_id
    response = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.CONTACT_INTERACTION,
            document_id=get_contacts_anchor_id(user.get_effective_user_id()),
            vault_path=get_contacts_vault_path(),
            payload=payload,
            metadata={
                "contact_id": contact.overlay_id,
                "interaction_type": payload.get("interaction_type"),
                "scope": "contacts",
            },
        )
    )
    if not response.success or not response.overlay_id:
        logger.error("Failed to log interaction for user %s: %s", user.user_id[:8], response.message)
        raise RuntimeError(f"Could not save interaction: {response.message}")

    # Update contact's last interaction date and count (legacy semantics).
    contact.payload["last_contact_date"] = payload.get("interaction_date")
    contact.payload["interaction_count"] = int(contact.payload.get("interaction_count") or 0) + 1
    contact.payload["updated_at"] = utc_now().isoformat()
    await manager.update_overlay(contact.overlay_id, payload=contact.payload)

    return await manager.get_overlay(response.overlay_id)


async def list_interactions(user: UserContext, contact_id: str) -> list[UnifiedOverlay]:
    """Interactions for a contact, newest first. Empty list if contact is
    missing or not owned (caller decides the 404)."""
    manager = await _get_overlay_manager(user)
    contact = await _resolve_contact(manager, user, contact_id)
    if contact is None:
        return []

    wanted = _contact_ids(contact)
    response = await manager.get_overlays(
        document_id=get_contacts_anchor_id(user.get_effective_user_id()),
        overlay_type=OverlayType.CONTACT_INTERACTION,
    )
    if not response.success:
        return []
    interactions = [
        o
        for o in response.overlays
        if _owns(user, o, OverlayType.CONTACT_INTERACTION) and o.payload.get("contact_id") in wanted
    ]
    interactions.sort(key=lambda o: o.payload.get("interaction_date") or "", reverse=True)
    return interactions


async def find_contact_by_name_type(user_id: str, name: str, contact_type: str) -> UnifiedOverlay | None:
    """Dedup lookup for extracted-contact writers (document_flow_orchestrator).
    Returns the first matching active contact, or None."""
    contacts, _total = await list_contacts_for_user_id(user_id, contact_type=contact_type)
    for c in contacts:
        if (c.payload.get("name") or "") == name:
            return c
    return None


async def create_contact_for_user_id(user_id: str, **fields) -> UnifiedOverlay | None:
    """create_contact for callers that only have a user_id
    (document_flow_orchestrator extraction pipeline)."""
    from app.core.user_context import build_context_for_user_id

    context = await build_context_for_user_id(user_id)
    if context is None:
        return None
    try:
        return await create_contact(context, **fields)
    except Exception as e:
        logger.error("Auto contact create failed for %s***: %s", user_id[:6], e)
        return None


# ---------------------------------------------------------------------------
# Legacy database migration (non-destructive, idempotent)
# ---------------------------------------------------------------------------


async def migrate_legacy_contacts(user: UserContext, max_rows: int = 25) -> int:
    """Import legacy contacts + contact_interactions rows into vault overlays.

    Bounded to ``max_rows`` per call (provider-work budget); idempotent via
    ``payload.legacy_id``. Interaction payloads keep their legacy contact_id —
    it still resolves through the migrated contact's payload id.
    """
    effective_id = user.get_effective_user_id()
    try:
        async with get_db_session() as db:
            contacts_result = await db.execute(
                select(ContactModel).where(ContactModel.user_id == effective_id)
            )
            contact_rows = list(contacts_result.scalars().all())
            interactions_result = await db.execute(
                select(ContactInteractionModel).where(ContactInteractionModel.user_id == effective_id)
            )
            interaction_rows = list(interactions_result.scalars().all())
    except Exception as e:
        logger.warning("Legacy contacts migration skipped for %s***: %s", effective_id[:6], e)
        return 0
    if not contact_rows and not interaction_rows:
        return 0

    manager = await _get_overlay_manager(user)
    existing_contacts = await manager.get_overlays(
        document_id=get_contacts_anchor_id(effective_id),
        overlay_type=OverlayType.CONTACT,
    )
    migrated_contact_ids = {
        o.payload.get("legacy_id")
        for o in existing_contacts.overlays
        if _owns(user, o, OverlayType.CONTACT) and o.payload.get("legacy_id")
    }
    existing_interactions = await manager.get_overlays(
        document_id=get_contacts_anchor_id(effective_id),
        overlay_type=OverlayType.CONTACT_INTERACTION,
    )
    migrated_interaction_ids = {
        o.payload.get("legacy_id")
        for o in existing_interactions.overlays
        if _owns(user, o, OverlayType.CONTACT_INTERACTION) and o.payload.get("legacy_id")
    }

    imported = 0
    for row in contact_rows:
        if imported >= max_rows:
            break
        if row.id in migrated_contact_ids:
            continue
        response = await manager.create_overlay(
            CreateOverlayRequest(
                overlay_type=OverlayType.CONTACT,
                document_id=get_contacts_anchor_id(effective_id),
                vault_path=get_contacts_vault_path(),
                payload={
                    "id": row.id,
                    "legacy_id": row.id,
                    "contact_type": row.contact_type,
                    "role": row.role,
                    "name": row.name,
                    "organization": row.organization,
                    "title": row.title,
                    "phone": row.phone,
                    "phone_alt": row.phone_alt,
                    "email": row.email,
                    "fax": row.fax,
                    "address_line1": row.address_line1,
                    "address_line2": row.address_line2,
                    "city": row.city,
                    "state": row.state,
                    "zip_code": row.zip_code,
                    "website": row.website,
                    "notes": row.notes,
                    "tags": row.tags,
                    "source": row.source or "manual",
                    "source_document_id": row.source_document_id,
                    "last_contact_date": row.last_contact_date.isoformat() if row.last_contact_date else None,
                    "interaction_count": row.interaction_count or 0,
                    "is_active": bool(row.is_active),
                    "is_starred": bool(row.is_starred),
                },
                metadata={
                    "migrated_from": "contacts",
                    "legacy_created_at": row.created_at.isoformat() if row.created_at else None,
                    "scope": "contacts",
                },
            )
        )
        if response.success:
            imported += 1
        else:
            logger.error("Failed to migrate contact row %s: %s", row.id, response.message)

    for row in interaction_rows:
        if imported >= max_rows:
            break
        if row.id in migrated_interaction_ids:
            continue
        response = await manager.create_overlay(
            CreateOverlayRequest(
                overlay_type=OverlayType.CONTACT_INTERACTION,
                document_id=get_contacts_anchor_id(effective_id),
                vault_path=get_contacts_vault_path(),
                payload={
                    "id": row.id,
                    "legacy_id": row.id,
                    "contact_id": row.contact_id,
                    "interaction_type": row.interaction_type,
                    "direction": row.direction,
                    "subject": row.subject,
                    "summary": row.summary,
                    "interaction_date": row.interaction_date.isoformat() if row.interaction_date else None,
                    "duration_minutes": row.duration_minutes,
                    "related_document_ids": row.related_document_ids,
                    "follow_up_needed": bool(row.follow_up_needed),
                    "follow_up_date": row.follow_up_date.isoformat() if row.follow_up_date else None,
                    "follow_up_notes": row.follow_up_notes,
                },
                metadata={
                    "migrated_from": "contact_interactions",
                    "legacy_created_at": row.created_at.isoformat() if row.created_at else None,
                    "scope": "contacts",
                },
            )
        )
        if response.success:
            imported += 1
        else:
            logger.error("Failed to migrate interaction row %s: %s", row.id, response.message)

    if imported:
        logger.info("Migrated %d legacy contact records to vault for user %s", imported, effective_id[:8])
    return imported
