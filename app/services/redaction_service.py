"""
Semptify 5.0 - Asymmetric Redaction Service

Task 9 of the Master Handoff: strip the authenticating user's own identifying
information from imported text while preserving third-party (landlord, agency,
attorney, etc.) contact data.

Design:
- Layer 1: exact-match redaction of the user's known email, phone, and name.
- Layer 2: heuristic PII pattern detection for other self-identifying data.
- Allowlist: ThirdPartyContact entries are protected so they are not redacted,
  even if they resemble generic PII patterns.

The service does NOT store any user PII. Callers supply the user's contact
clues at runtime (for example, from an OAuth profile or the importing source);
third-party allowlist entries are read from the ThirdPartyContact table.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.module_contracts import FunctionGroupContract, register_function_group
from app.core.utc import utc_now
from app.models.models import ThirdPartyContact

logger = logging.getLogger(__name__)

REDACTION_FUNCTION_GROUP = "redaction"


# =============================================================================
# Redaction placeholders (human-readable, plain language)
# =============================================================================

REDACTED_EMAIL = "[REDACTED: email]"
REDACTED_PHONE = "[REDACTED: phone]"
REDACTED_NAME = "[REDACTED: name]"
REDACTED_PII = "[REDACTED: identifying info]"


# =============================================================================
# Regex patterns for heuristic PII detection (Layer 2)
# =============================================================================

# Email address, reasonably strict.
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# US-style phone numbers. Matches common formats:
# (555) 123-4567, 555-123-4567, 555.123.4567, 555 123 4567, 5551234567, +1 555 123 4567
_PHONE_RE = re.compile(
    r"(?:\+1[-.\s]?)?\(?[2-9][0-8][0-9]\)?[-.\s]?[2-9][0-9]{2}[-.\s]?[0-9]{4}",
    re.IGNORECASE,
)

# SSN-like pattern (XXX-XX-XXXX). Note: this is intentionally narrow to avoid
# false positives; a user could redact other numeric forms in a future pass.
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


class RedactionService:
    """
    Asymmetric redaction engine.

    Example:
        service = RedactionService(
            user_email="tenant@example.com",
            user_phone="555-123-4567",
            user_name="Jane Doe",
            allowlist=["landlord@example.com", "555-765-4321"],
        )
        clean = service.redact("Jane Doe emailed landlord@example.com from 555-123-4567.")
    """

    def __init__(
        self,
        user_email: Optional[str] = None,
        user_phone: Optional[str] = None,
        user_name: Optional[str] = None,
        allowlist: Optional[list[str]] = None,
    ) -> None:
        self.user_email = user_email
        self.user_phone = user_phone
        self.user_name = user_name
        # Normalize allowlist: keep non-empty values, case-fold for dedup but
        # preserve original casing for display restoration.
        self.allowlist: list[str] = []
        self._allowlist_lower: set[str] = set()
        for item in allowlist or []:
            stripped = item.strip()
            if stripped and stripped.lower() not in self._allowlist_lower:
                self.allowlist.append(stripped)
                self._allowlist_lower.add(stripped.lower())

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def redact(self, text: str) -> str:
        """Return redacted copy of ``text``."""
        if not text:
            return text

        # Step 1: protect allowlisted third-party strings so heuristic redaction
        # does not accidentally remove them.
        protected, tokens = self._protect_allowlist(text)

        # Step 2: redact user's own known contact info (Layer 1).
        layer1 = self._redact_user_known(protected)

        # Step 3: heuristic PII detection (Layer 2).
        layer2 = self._redact_heuristic_pii(layer1)

        # Step 4: restore allowlisted strings.
        return self._restore_allowlist(layer2, tokens)

    # Keep ``redact_text`` as an alias for callers that prefer that name.
    redact_text = redact

    # -------------------------------------------------------------------------
    # Layer helpers
    # -------------------------------------------------------------------------

    def _protect_allowlist(self, text: str) -> tuple[str, dict[str, str]]:
        """
        Replace allowlisted strings with unique tokens so downstream redaction
        cannot touch them. Returns (protected_text, token_map).
        """
        tokens: dict[str, str] = {}
        protected = text
        for idx, value in enumerate(self.allowlist):
            if not value:
                continue
            token = f"__ALLOWLIST_TOKEN_{idx}_{hex(abs(hash(value)) % (2**32)).lstrip('0x').upper()}__"
            tokens[token] = value
            # Case-insensitive replacement to catch Landlord@Example.com etc.
            pattern = re.escape(value)
            protected = re.sub(pattern, token, protected, flags=re.IGNORECASE)
        return protected, tokens

    @staticmethod
    def _restore_allowlist(text: str, tokens: dict[str, str]) -> str:
        """Replace allowlist tokens with their original values."""
        restored = text
        for token, value in tokens.items():
            restored = restored.replace(token, value)
        return restored

    def _redact_user_known(self, text: str) -> str:
        """Layer 1: exact-match redaction of the user's supplied contact info."""
        result = text

        if self.user_email:
            # Whole-word-ish boundary for email: require non-word char or start/end.
            pattern = re.compile(
                r"(?<![a-zA-Z0-9._%+-])" + re.escape(self.user_email) + r"(?![a-zA-Z0-9._%+\-])",
                re.IGNORECASE,
            )
            result = pattern.sub(REDACTED_EMAIL, result)

        if self.user_phone:
            # Normalize to digits for matching, then replace the literal display form.
            normalized_digits = _digits_only(self.user_phone)
            if normalized_digits:
                # Build a permissive regex matching the user's number in common formats.
                permutations = _phone_permutations(normalized_digits)
                for perm in permutations:
                    result = re.sub(
                        re.escape(perm),
                        REDACTED_PHONE,
                        result,
                        flags=re.IGNORECASE,
                    )

        if self.user_name and len(self.user_name) > 1:
            # Match full name as a phrase. Also try "Last, First" and "First Last".
            names = _name_variants(self.user_name)
            for name in names:
                pattern = re.compile(r"\b" + re.escape(name) + r"\b", re.IGNORECASE)
                result = pattern.sub(REDACTED_NAME, result)

        return result

    def _redact_heuristic_pii(self, text: str) -> str:
        """Layer 2: generic PII pattern detection, skipping already-redacted blocks."""
        result = text

        # Emails
        result = _EMAIL_RE.sub(REDACTED_EMAIL, result)

        # Phone numbers
        result = _PHONE_RE.sub(REDACTED_PHONE, result)

        # SSN-like numbers
        result = _SSN_RE.sub(REDACTED_PII, result)

        return result


# =============================================================================
# Allowlist loading from ThirdPartyContact table
# =============================================================================

async def build_allowlist_for_user(
    user_id: str,
    db: Optional[AsyncSession] = None,
    case_record_id: Optional[str] = None,
) -> list[str]:
    """
    Load active ThirdPartyContact entries for a user as an allowlist.

    If ``case_record_id`` is provided, contacts linked to that case are included
    first; the query still falls back to all user contacts because imported
    communications often involve parties across cases.
    """
    from app.core.database import get_db_session

    close_session = db is None
    session = db
    try:
        if session is None:
            cm = get_db_session()
            session = await cm.__aenter__()

        stmt = select(ThirdPartyContact).where(
            ThirdPartyContact.user_id == user_id,
            ThirdPartyContact.is_active == True,  # noqa: E712
        )
        if case_record_id:
            stmt = stmt.where(
                (ThirdPartyContact.case_record_id == case_record_id)
                | (ThirdPartyContact.case_record_id.is_(None))
            )
        result = await session.execute(stmt)
        contacts = result.scalars().all()
    finally:
        if close_session and session is not None:
            await session.close()

    allowlist: set[str] = set()
    for contact in contacts:
        for value in (contact.email, contact.phone, contact.name, contact.address):
            if value:
                allowlist.add(value.strip())
    return sorted(allowlist)


async def redact_text_for_user(
    user_id: str,
    text: str,
    user_email: Optional[str] = None,
    user_phone: Optional[str] = None,
    user_name: Optional[str] = None,
    case_record_id: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> str:
    """
    Convenience helper: build the allowlist from ``ThirdPartyContact`` and
    redact ``text`` in one call.
    """
    allowlist = await build_allowlist_for_user(
        user_id=user_id,
        db=db,
        case_record_id=case_record_id,
    )
    service = RedactionService(
        user_email=user_email,
        user_phone=user_phone,
        user_name=user_name,
        allowlist=allowlist,
    )
    return service.redact(text)


# =============================================================================
# Utility helpers
# =============================================================================

def _digits_only(value: str) -> str:
    """Strip non-digit characters from a phone number."""
    return "".join(ch for ch in value if ch.isdigit())


def _phone_permutations(digits: str) -> list[str]:
    """Generate common display formats for a 10-digit US phone number."""
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return [digits]

    area = digits[0:3]
    prefix = digits[3:6]
    line = digits[6:10]
    return [
        f"({area}) {prefix}-{line}",
        f"{area}-{prefix}-{line}",
        f"{area}.{prefix}.{line}",
        f"{area} {prefix} {line}",
        f"{area}{prefix}{line}",
        f"1 ({area}) {prefix}-{line}",
        f"+1 ({area}) {prefix}-{line}",
        f"+1 {area}-{prefix}-{line}",
        f"{area} {prefix}-{line}",
    ]


def _name_variants(name: str) -> list[str]:
    """Return common orderings and punctuation variants of a full name."""
    parts = name.strip().split()
    variants = [name]
    if len(parts) == 2:
        first, last = parts
        variants.extend([
            f"{last}, {first}",
            f"{first} {last}",
            f"{last} {first}",
        ])
    return list(dict.fromkeys(variants))


# =============================================================================
# Module contract registration
# =============================================================================

register_function_group(
    FunctionGroupContract(
        module="redaction",
        group_name=REDACTION_FUNCTION_GROUP,
        title="Asymmetric Redaction Service (SSOT)",
        description=(
            "Strip the authenticating user's own identifying information from text "
            "while preserving third-party contact data using a ThirdPartyContact allowlist. "
            "Layer 1 matches user-supplied email/phone/name. Layer 2 uses heuristic "
            "patterns for email, phone, and SSN-like numbers."
        ),
        inputs=(
            "text",
            "user_id",
            "user_email?",
            "user_phone?",
            "user_name?",
            "case_record_id?",
            "db?",
        ),
        outputs=("redacted_text",),
        dependencies=("app.services.redaction_service", "app.models.models.ThirdPartyContact"),
        deterministic=True,
    )
)
