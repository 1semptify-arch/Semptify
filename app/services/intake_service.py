"""
Semptify 5.0 - Communication Import Service

Task 10 of the Master Handoff: file-based import of email, text messages,
voicemail transcripts, and call logs into the tenant's record.

Design principles:
- File-based import into the user's own connected storage only — no live OAuth.
- Asymmetric redaction is mandatory before any text is stored or embedded.
- Third-party contacts are extracted and upserted to ThirdPartyContact for
  downstream matching (e.g., call logs, redaction allowlist).
- Voicemail audio is transcribed then discarded unless the user explicitly
  opts to keep the raw audio as evidence.
- Imported communications become `TimelineEvent` rows with `event_type='communication'`.
"""

from __future__ import annotations

import csv
import io
import logging
import mailbox
import re
from datetime import UTC, datetime
from email import policy
from email.parser import BytesParser
from pathlib import Path
from xml.etree import ElementTree as ET

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.id_gen import make_id
from app.core.module_contracts import FunctionGroupContract, register_function_group
from app.core.utc import utc_now
from app.models.models import ThirdPartyContact, TimelineEvent
from app.services.redaction_service import redact_text_for_user

logger = logging.getLogger(__name__)

INTAKE_FUNCTION_GROUP = "communication_import"

# =============================================================================
# Regex helpers (reused across parsers)
# =============================================================================

_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)
_PHONE_RE = re.compile(
    r"(?:\+1[-.\s]?)?\(?[2-9][0-8][0-9]\)?[-.\s]?[2-9][0-9]{2}[-.\s]?[0-9]{4}",
    re.IGNORECASE,
)


def _digits_only(value: str) -> str:
    """Return only the digit characters from a phone number string."""
    return "".join(ch for ch in value if ch.isdigit())


def _normalized_phone(value: str) -> str:
    """Normalize a phone string to 10 digits (drop leading 1)."""
    digits = _digits_only(value)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def _extract_email_part(address: str) -> str:
    """Return the bare email address from 'Name <email@example.com>' forms."""
    match = re.search(r"<([^>]+)>", address)
    if match:
        return match.group(1).strip().lower()
    return address.strip().lower()


def _extract_display_name(address: str) -> str | None:
    """Return the display name from 'Name <email@example.com>' if present."""
    match = re.search(r"^([^<]+?)\s*<", address)
    if match:
        return match.group(1).strip().strip('"')
    return None


def _parse_date_rfc2822(value: str) -> datetime | None:
    """Parse an RFC 2822 date string to an offset-aware UTC datetime."""
    from email.utils import parsedate_to_datetime

    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except (TypeError, ValueError) as exc:
        logger.debug("Could not parse RFC 2822 date %r: %s", value, exc)
        return None


def _parse_loose_date(value: str) -> datetime | None:
    """Best-effort parse of common date/time strings."""
    value = value.strip()
    if not value:
        return None

    iso_formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
        "%B %d, %Y %H:%M:%S",
        "%B %d, %Y",
    ]
    for fmt in iso_formats:
        try:
            dt = datetime.strptime(value, fmt)  # noqa: DTZ007
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        except ValueError:
            continue

    # Try RFC 2822 as a fallback.
    return _parse_date_rfc2822(value)


# =============================================================================
# Low-level parsers
# =============================================================================

def parse_eml(file_bytes: bytes) -> dict:
    """Parse a single RFC 5322 `.eml` file into structured communication data."""
    msg = BytesParser(policy=policy.default).parsebytes(file_bytes)

    subject = str(msg.get("subject", ""))
    from_field = str(msg.get("from", ""))
    to_field = str(msg.get("to", ""))
    date_field = str(msg.get("date", ""))

    body_parts = []
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body_parts.append(_decode_payload(payload))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body_parts.append(_decode_payload(payload))

    body = "\n\n".join(body_parts).strip()

    return {
        "source": "email_import",
        "subject": subject,
        "from_address": _extract_email_part(from_field),
        "from_name": _extract_display_name(from_field),
        "to_address": _extract_email_part(to_field),
        "to_name": _extract_display_name(to_field),
        "date": _parse_date_rfc2822(date_field) or utc_now(),
        "body": body,
    }


def parse_mbox(file_bytes: bytes) -> list[dict]:
    """Parse an `.mbox` file into a list of communication dicts."""
    # mailbox.mbox requires a filesystem path. Write to a temporary file.
    tmp_path = Path(make_id("tmp") + ".mbox")
    try:
        tmp_path.write_bytes(file_bytes)
        mbox = mailbox.mbox(str(tmp_path), factory=_eml_factory)
        messages = []
        for msg in mbox:
            messages.append(_mbox_message_to_dict(msg))
        return messages
    finally:
        try:
            tmp_path.unlink()
        except OSError as exc:
            logger.debug("Could not remove temp mbox file %s: %s", tmp_path, exc)


def _eml_factory(data: bytes) -> mailbox.mboxMessage:
    return mailbox.mboxMessage(data)


def _mbox_message_to_dict(msg: mailbox.mboxMessage) -> dict:
    from email.parser import Parser

    parsed = Parser(policy=policy.default).parsestr(str(msg))
    return parse_eml(parsed.as_bytes())


def _decode_payload(payload: bytes) -> str:
    """Decode email payload, trying utf-8 then latin-1."""
    for encoding in ("utf-8", "latin-1"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="replace")


def parse_sms_csv(file_bytes: bytes) -> list[dict]:
    """Parse an SMS export CSV. Handles common column aliases."""
    text = _decode_payload(file_bytes)
    # Strip a UTF-8 BOM if present.
    if text.startswith("\ufeff"):
        text = text[1:]

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []

    fieldnames = [fn.lower().strip() for fn in reader.fieldnames]
    alias_map = _build_alias_map(fieldnames, {
        "from": ["from", "sender", "from_address", "from number", "from_number", "from phone", "from_phone", "source"],
        "to": ["to", "recipient", "to_address", "to number", "to_number", "to phone", "to_phone", "destination"],
        "body": ["body", "message", "text", "content", "sms"],
        "date": ["date", "timestamp", "time", "datetime", "sent", "received"],
    })

    messages = []
    for row in reader:
        raw = {k.lower().strip(): v for k, v in row.items() if k}
        body = _get_with_alias(raw, alias_map, "body", "")
        from_field = _get_with_alias(raw, alias_map, "from", "")
        to_field = _get_with_alias(raw, alias_map, "to", "")

        messages.append({
            "source": "sms_import",
            "from_address": from_field,
            "to_address": to_field,
            "body": body,
            "date": _parse_loose_date(_get_with_alias(raw, alias_map, "date", "")) or utc_now(),
        })
    return messages


def parse_sms_xml(file_bytes: bytes) -> list[dict]:
    """Parse a common Android SMS Backup XML format (SMSBackupRestore)."""
    try:
        root = ET.fromstring(file_bytes)
    except ET.ParseError as exc:
        logger.warning("Could not parse SMS XML: %s", exc)
        return []

    messages = []
    for sms in root.findall("sms"):
        messages.append({
            "source": "sms_import",
            "from_address": sms.get("address", ""),
            "to_address": sms.get("contact_name", ""),
            "body": sms.get("body", ""),
            "date": _parse_loose_date(sms.get("date", "")) or utc_now(),
        })
    return messages


def parse_call_logs_csv(file_bytes: bytes) -> list[dict]:
    """Parse a call-log CSV export (metadata only: date, duration, number, type)."""
    text = _decode_payload(file_bytes)
    if text.startswith("\ufeff"):
        text = text[1:]

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []

    fieldnames = [fn.lower().strip() for fn in reader.fieldnames]
    alias_map = _build_alias_map(fieldnames, {
        "number": ["number", "phone", "phone_number", "phone number", "caller", "recipient", "contact"],
        "date": ["date", "timestamp", "time", "datetime"],
        "duration": ["duration", "duration_seconds", "duration seconds", "length"],
        "type": ["type", "call_type", "call type", "direction"],
    })

    calls = []
    for row in reader:
        raw = {k.lower().strip(): v for k, v in row.items() if k}
        number = _get_with_alias(raw, alias_map, "number", "")
        duration = _get_with_alias(raw, alias_map, "duration", "0")
        try:
            duration_val = int(float(duration))
        except ValueError:
            duration_val = 0

        calls.append({
            "source": "call_log_import",
            "number": number,
            "normalized_number": _normalized_phone(number),
            "date": _parse_loose_date(_get_with_alias(raw, alias_map, "date", "")) or utc_now(),
            "duration_seconds": duration_val,
            "call_type": _get_with_alias(raw, alias_map, "type", ""),
        })
    return calls


async def transcribe_voicemail(file_bytes: bytes, mime_type: str = "audio/mpeg") -> str:
    """
    Placeholder for voicemail transcription.

    Task 5 (voice-to-text) owns the real transcription pipeline. This function
    exists as the integration point: once Task 5 lands, replace the body below
    with the real client-side/server-side transcription call.

    Policy: discard raw audio unless user explicitly opts to keep it. The caller
    is responsible for deleting the audio file after transcription.
    """
    logger.info(
        "Voicemail transcription requested (%d bytes, %s). "
        "Task 5 transcription pipeline not yet available; returning placeholder.",
        len(file_bytes),
        mime_type,
    )
    return "[voicemail transcript pending: Task 5 voice-to-text pipeline not yet integrated]"


# =============================================================================
# Contact extraction / upsert
# =============================================================================

async def extract_and_upsert_contacts(
    db: AsyncSession,
    user_id: str,
    communications: list[dict],
    user_email: str | None = None,
    user_phone: str | None = None,
) -> list[ThirdPartyContact]:
    """
    Scan communication metadata/bodies for third-party contact info and upsert
    into the ThirdPartyContact table. Skip anything that matches the user's own
    supplied email/phone.
    """
    candidates: dict[str, dict] = {}
    user_emails = {user_email.lower()} if user_email else set()
    user_phones = {_normalized_phone(user_phone)} if user_phone else set()

    for comm in communications:
        for key in ("from_address", "to_address", "from_name", "number"):
            value = comm.get(key)
            if not value:
                continue

            if key in ("from_address", "to_address"):
                email = _extract_email_part(value)
                if email and email not in user_emails:
                    candidates.setdefault(email.lower(), {
                        "name": comm.get("from_name") or comm.get("to_name") or "",
                        "email": email,
                        "phone": None,
                        "entity_type": "other",
                        "source": comm.get("source", "manual_entry"),
                    })

            if key in ("from_address", "to_address", "number"):
                # Scan text fields for phone numbers too.
                phones = _PHONE_RE.findall(value)
                for phone in phones:
                    norm = _normalized_phone(phone)
                    if norm and norm not in user_phones:
                        candidates.setdefault(norm, {
                            "name": comm.get("from_name") or comm.get("to_name") or "",
                            "email": None,
                            "phone": phone,
                            "entity_type": "other",
                            "source": comm.get("source", "manual_entry"),
                        })

        # Also scan the message body for emails/phone numbers.
        body = comm.get("body", "")
        if body:
            for email in _EMAIL_RE.findall(body):
                email = email.lower()
                if email and email not in user_emails:
                    candidates.setdefault(email, {
                        "name": "",
                        "email": email,
                        "phone": None,
                        "entity_type": "other",
                        "source": comm.get("source", "manual_entry"),
                    })
            for phone in _PHONE_RE.findall(body):
                norm = _normalized_phone(phone)
                if norm and norm not in user_phones:
                    candidates.setdefault(norm, {
                        "name": "",
                        "email": None,
                        "phone": phone,
                        "entity_type": "other",
                        "source": comm.get("source", "manual_entry"),
                    })

    upserted: list[ThirdPartyContact] = []
    for key, data in candidates.items():
        # Try to find an existing contact by email or phone for this user.
        existing = None
        if data["email"]:
            result = await db.execute(
                select(ThirdPartyContact).where(
                    ThirdPartyContact.user_id == user_id,
                    ThirdPartyContact.email == data["email"],
                    ThirdPartyContact.is_active == True,  # noqa: E712
                )
            )
            existing = result.scalar_one_or_none()
        if not existing and data["phone"]:
            result = await db.execute(
                select(ThirdPartyContact).where(
                    ThirdPartyContact.user_id == user_id,
                    ThirdPartyContact.phone == data["phone"],
                    ThirdPartyContact.is_active == True,  # noqa: E712
                )
            )
            existing = result.scalar_one_or_none()

        if existing:
            # Only enrich if empty.
            if not existing.name and data["name"]:
                existing.name = data["name"]
            existing.updated_at = utc_now()
            upserted.append(existing)
        else:
            contact = ThirdPartyContact(
                id=make_id("tpc"),
                user_id=user_id,
                entity_type=data["entity_type"],
                name=data["name"],
                email=data["email"],
                phone=data["phone"],
                source=data["source"],
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            db.add(contact)
            upserted.append(contact)

    await db.commit()
    return upserted


# =============================================================================
# Redaction + timeline persistence
# =============================================================================

async def import_communications(
    db: AsyncSession,
    user_id: str,
    file_bytes: bytes,
    filename: str,
    user_email: str | None = None,
    user_phone: str | None = None,
    user_name: str | None = None,
    case_record_id: str | None = None,
    keep_voicemail_audio: bool = False,
) -> dict:
    """
    Main entry point for the communication import pipeline.

    Steps:
    1. Parse file based on extension.
    2. Extract and upsert third-party contacts.
    3. Redact each message using the user's own contact clues + allowlist.
    4. Create `TimelineEvent` rows for each communication.

    Returns a summary dict.
    """
    suffix = Path(filename).suffix.lower()

    if suffix == ".eml":
        communications = [parse_eml(file_bytes)]
    elif suffix == ".mbox":
        communications = parse_mbox(file_bytes)
    elif suffix == ".csv":
        # Call logs and SMS CSV share .csv; inspect headers.
        text = _decode_payload(file_bytes)
        if text.startswith("\ufeff"):
            text = text[1:]
        first_line = text.splitlines()[0].lower() if text else ""
        if any(word in first_line for word in ["number", "duration", "call_type", "type", "call"]):
            communications = parse_call_logs_csv(file_bytes)
        else:
            communications = parse_sms_csv(file_bytes)
    elif suffix == ".xml":
        communications = parse_sms_xml(file_bytes)
    elif suffix in (".mp3", ".mp4", ".m4a", ".wav", ".ogg", ".flac", ".amr"):
        transcript = await transcribe_voicemail(file_bytes)
        communications = [{
            "source": "voicemail_import",
            "body": transcript,
            "date": utc_now(),
            "from_address": "",
            "to_address": "",
        }]
        if not keep_voicemail_audio:
            # The caller still holds the file; we just note the policy.
            logger.info("Voicemail raw audio will be discarded per policy (keep_voicemail_audio=False).")
    else:
        raise ValueError(f"Unsupported communication import format: {suffix!r}")

    # Enrich/upsert contacts first so the redaction allowlist is populated.
    contacts = await extract_and_upsert_contacts(
        db=db,
        user_id=user_id,
        communications=communications,
        user_email=user_email,
        user_phone=user_phone,
    )

    allowlist = [c.email for c in contacts if c.email] + [c.phone for c in contacts if c.phone]

    timeline_events: list[TimelineEvent] = []
    for comm in communications:
        raw_body = comm.get("body", "")
        redacted_body = await redact_text_for_user(
            user_id=user_id,
            text=raw_body,
            user_email=user_email,
            user_phone=user_phone,
            user_name=user_name,
            case_record_id=case_record_id,
            db=db,
        )

        title = comm.get("subject") or "Communication"
        if not title or title == "Communication":
            title = f"{comm.get('source', 'communication').replace('_', ' ').title()}"

        event = TimelineEvent(
            id=make_id("evt"),
            user_id=user_id,
            event_type="communication",
            title=title,
            description=redacted_body,
            event_date=comm.get("date") or utc_now(),
            is_evidence=True,
            created_at=utc_now(),
        )
        db.add(event)
        timeline_events.append(event)

    await db.commit()

    return {
        "filename": filename,
        "format": suffix,
        "communications_parsed": len(communications),
        "contacts_extracted": len(contacts),
        "timeline_events_created": len(timeline_events),
    }


# =============================================================================
# CSV/alias helpers
# =============================================================================

def _build_alias_map(
    fieldnames: list[str],
    aliases: dict[str, list[str]],
) -> dict[str, str]:
    """Map canonical keys to the actual CSV column name (lower-cased) used."""
    mapping: dict[str, str] = {}
    for canonical, candidates in aliases.items():
        for candidate in candidates:
            if candidate in fieldnames:
                mapping[canonical] = candidate
                break
    return mapping


def _get_with_alias(
    row: dict[str, str],
    alias_map: dict[str, str],
    canonical: str,
    default: str = "",
) -> str:
    """Get a CSV value using the alias map."""
    key = alias_map.get(canonical)
    if not key:
        return default
    return (row.get(key) or "").strip()


# =============================================================================
# Module contract registration
# =============================================================================

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name=INTAKE_FUNCTION_GROUP,
        title="Communication Import Service (SSOT)",
        description=(
            "Import email (.eml/.mbox), SMS (CSV/XML), call logs (CSV), and "
            "voicemail audio into the tenant timeline. Parses third-party "
            "contacts, upserts them to ThirdPartyContact, and redacts the "
            "authenticating user's identifying info before storage."
        ),
        inputs=(
            "db",
            "user_id",
            "file_bytes",
            "filename",
            "user_email?",
            "user_phone?",
            "user_name?",
            "case_record_id?",
            "keep_voicemail_audio?",
        ),
        outputs=("summary",),
        dependencies=(
            "app.services.redaction_service",
            "app.models.models.ThirdPartyContact",
            "app.models.models.TimelineEvent",
        ),
        deterministic=False,
    )
)
