"""Info Donation service — gate, consent, donate, review, withdraw.

All functions take an ``AsyncSession`` (the route layer owns the session
via ``get_db``). Rules enforced here:

- No donation is accepted unless the tenant's situation is resolved AND
  informed consent is on file AND consent has not been revoked.
- ``item_key`` must be in ``catalog.DONATION_ITEMS`` and the value must
  match the declared kind/options — unknown keys and out-of-catalog values
  are rejected, never stored.
- Free text is screened for email/phone/SSN/street-address patterns and
  rejected outright (don't store it and rely on moderation to catch it).
- Withdrawal hard-deletes rows — the tenant's donated data is theirs.
"""

import json
import logging
import re
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.id_gen import make_id
from app.core.utc import utc_now
from app.modules.info_donation.catalog import CONSENT_VERSION, DONATION_ITEMS, MAX_TEXT_LENGTH
from app.modules.info_donation.models import InfoDonationItem, InfoDonationProfile

logger = logging.getLogger(__name__)


class DonationError(ValueError):
    """Raised for validation failures the tenant can act on (bad item key,
    value shape, consent missing). Carries a plain-language message."""


# Minimal PII screens for free text — these are deliberately conservative:
# a miss here still lands in the human moderation queue.
_PII_PATTERNS: tuple[tuple[str, re.Pattern], ...] = (
    ("an email address", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
    ("a phone number", re.compile(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")),
    ("a Social Security number", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    (
        "a street address",
        re.compile(
            r"\b\d{1,6}\s+\w+(\s+\w+)*\s+(street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|court|ct|way|place|pl)\b",
            re.IGNORECASE,
        ),
    ),
)


def _screen_text(item_key: str, value: str) -> None:
    """Reject free text that looks like it contains PII."""
    for what, pattern in _PII_PATTERNS:
        if pattern.search(value):
            raise DonationError(
                f"'{item_key}' looks like it contains {what}. "
                "Please keep answers general — no names, addresses, or phone numbers."
            )


def _validate_value(item_key: str, value: Any) -> Any:
    """Validate a donated value against the catalog. Returns the normalized
    value or raises DonationError."""
    item = DONATION_ITEMS.get(item_key)
    if item is None:
        raise DonationError(f"Unknown donation item '{item_key}'.")

    kind = item["kind"]
    if kind == "choice":
        if not isinstance(value, str) or value not in item["options"]:
            raise DonationError(f"'{item_key}' must be one of: {', '.join(item['options'])}.")
        return value
    if kind == "multichoice":
        if not isinstance(value, list) or not value:
            raise DonationError(f"'{item_key}' must be a non-empty list.")
        bad = [v for v in value if not isinstance(v, str) or v not in item["options"]]
        if bad:
            raise DonationError(f"'{item_key}' contains unknown choices: {', '.join(map(str, bad))}.")
        return value
    if kind == "bool":
        if not isinstance(value, bool):
            raise DonationError(f"'{item_key}' must be true or false.")
        return value
    if kind == "text":
        if not isinstance(value, str) or not value.strip():
            raise DonationError(f"'{item_key}' must be text.")
        value = value.strip()
        if len(value) > MAX_TEXT_LENGTH:
            raise DonationError(f"'{item_key}' is too long (max {MAX_TEXT_LENGTH} characters).")
        _screen_text(item_key, value)
        return value
    raise DonationError(f"'{item_key}' has an unsupported kind.")


async def get_or_create_profile(db: AsyncSession, user_id: str) -> InfoDonationProfile:
    """Fetch the donation profile, creating an empty one if needed."""
    profile = await db.get(InfoDonationProfile, user_id)
    if profile is None:
        profile = InfoDonationProfile(user_id=user_id)
        db.add(profile)
        await db.flush()
    return profile


async def get_status(db: AsyncSession, user_id: str) -> dict[str, Any]:
    """Status snapshot for the UI gate: resolved? dismissed? consented?"""
    profile = await db.get(InfoDonationProfile, user_id)
    result = await db.execute(
        select(InfoDonationItem.id).where(InfoDonationItem.user_id == user_id)
    )
    item_count = len(result.scalars().all())

    resolved = bool(profile and profile.resolved_at)
    dismissed = bool(profile and profile.prompt_dismissed_at)
    consented = bool(profile and profile.consented_at and not profile.consent_revoked_at)
    return {
        "resolved": resolved,
        "dismissed": dismissed,
        "consented": consented,
        "eligible": resolved and not dismissed,
        "item_count": item_count,
        "consent_version": profile.consent_version if profile else None,
        "current_consent_version": CONSENT_VERSION,
    }


async def mark_resolved(db: AsyncSession, user_id: str, source: str = "self_reported") -> bool:
    """Record that the tenant's situation is resolved. Idempotent — the
    first resolution wins (a later re-resolution does not move the date)."""
    profile = await get_or_create_profile(db, user_id)
    if profile.resolved_at is not None:
        return False
    profile.resolved_at = utc_now()
    profile.resolved_source = source[:60]
    await db.commit()
    logger.info("Info donation: issue resolved for user %s (source=%s)", user_id[:8], source)
    return True


async def dismiss(db: AsyncSession, user_id: str) -> None:
    """Permanently dismiss the donation ask for this tenant."""
    profile = await get_or_create_profile(db, user_id)
    profile.prompt_dismissed_at = utc_now()
    await db.commit()


async def record_consent(db: AsyncSession, user_id: str, consent_version: str) -> InfoDonationProfile:
    """Record informed consent. Requires the resolution gate first and a
    matching consent version (the text the tenant actually saw)."""
    profile = await get_or_create_profile(db, user_id)
    if profile.resolved_at is None:
        raise DonationError("Sharing is only available after your situation is resolved.")
    if consent_version != CONSENT_VERSION:
        raise DonationError("Consent version mismatch — please reload the page and review the text again.")
    profile.consent_version = consent_version
    profile.consented_at = utc_now()
    profile.consent_revoked_at = None
    await db.commit()
    return profile


async def _require_donatable(db: AsyncSession, user_id: str) -> InfoDonationProfile:
    profile = await get_or_create_profile(db, user_id)
    if profile.resolved_at is None:
        raise DonationError("Sharing is only available after your situation is resolved.")
    if profile.prompt_dismissed_at is not None:
        raise DonationError("The donation prompt is turned off for you.")
    if not profile.consented_at or profile.consent_revoked_at:
        raise DonationError("Please review and accept the sharing note first.")
    return profile


async def submit_items(
    db: AsyncSession, user_id: str, items: dict[str, Any]
) -> list[InfoDonationItem]:
    """Validate and store donated items. Each key is independently opt-in;
    re-answering an item replaces the previous answer."""
    await _require_donatable(db, user_id)
    if not items:
        raise DonationError("Nothing was selected to share.")

    stored: list[InfoDonationItem] = []
    for item_key, raw_value in items.items():
        value = _validate_value(item_key, raw_value)
        needs_review = bool(DONATION_ITEMS[item_key]["needs_review"])

        result = await db.execute(
            select(InfoDonationItem).where(
                InfoDonationItem.user_id == user_id,
                InfoDonationItem.item_key == item_key,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = InfoDonationItem(id=make_id("idi"), user_id=user_id, item_key=item_key)
            db.add(row)
        row.value_json = json.dumps(value)
        # Re-answer resets moderation — a new free-text answer is unseen.
        row.moderation = "pending" if needs_review else "none"
        row.moderated_by = None
        row.moderated_at = None
        stored.append(row)

    await db.commit()
    logger.info("Info donation: stored %d item(s) for user %s", len(stored), user_id[:8])
    return stored


async def list_mine(db: AsyncSession, user_id: str) -> list[InfoDonationItem]:
    """The tenant's own donations, newest first."""
    result = await db.execute(
        select(InfoDonationItem)
        .where(InfoDonationItem.user_id == user_id)
        .order_by(InfoDonationItem.created_at.desc())
    )
    return list(result.scalars().all())


async def withdraw_item(db: AsyncSession, user_id: str, item_id: str) -> bool:
    """Delete one donated item. Only the owner's rows can be deleted."""
    result = await db.execute(
        delete(InfoDonationItem).where(
            InfoDonationItem.id == item_id,
            InfoDonationItem.user_id == user_id,
        )
    )
    await db.commit()
    return bool(result.rowcount)


async def withdraw_all(db: AsyncSession, user_id: str) -> int:
    """Take back everything: delete all items and revoke consent. The
    consent record stays (revoked) so the ledger shows consent was given
    then withdrawn."""
    profile = await get_or_create_profile(db, user_id)
    result = await db.execute(
        delete(InfoDonationItem).where(InfoDonationItem.user_id == user_id)
    )
    profile.consent_revoked_at = utc_now()
    await db.commit()
    return int(result.rowcount or 0)


# --- Reviewer surface (Brad + beta users; admin-gated at the router) ---


async def list_pending_review(db: AsyncSession) -> list[InfoDonationItem]:
    """Free-text donations waiting for human review."""
    result = await db.execute(
        select(InfoDonationItem)
        .where(InfoDonationItem.moderation == "pending")
        .order_by(InfoDonationItem.created_at)
    )
    return list(result.scalars().all())


async def moderate_item(
    db: AsyncSession, item_id: str, decision: str, reviewer_id: str
) -> InfoDonationItem | None:
    """Approve or reject a pending free-text donation."""
    if decision not in ("approved", "rejected"):
        raise DonationError("Decision must be 'approved' or 'rejected'.")
    item = await db.get(InfoDonationItem, item_id)
    if item is None:
        return None
    item.moderation = decision
    item.moderated_by = reviewer_id
    item.moderated_at = utc_now()
    await db.commit()
    return item
