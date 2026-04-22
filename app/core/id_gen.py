"""
Semptify ID Generation — Single Source of Truth
================================================
All entity IDs in the system MUST be generated through this module.

Format: {prefix}_{16-char alphanumeric}
Examples:
    make_id("doc")  → "doc_K8mXp2nR4jW7qF9a"
    make_id("ovl")  → "ovl_Tb3xM7kL9pR2wH5s"
    make_id("evt")  → "evt_Q4nJ8vR2mK6xP3wA"
    make_id("cert") → "cert_Y7hF3tN9bK2xR5mW"

Properties:
    - 16-char alphanumeric suffix = ~95 bits of entropy
    - No hyphens, URL-safe, filename-safe
    - Prefix identifies entity type at a glance
    - No truncated UUIDs, no collision risk

User IDs are NOT generated here — they use a separate scheme
in app/core/user_id.py (provider+role+8-char format).
"""

import secrets
import string

_ALPHABET = string.ascii_letters + string.digits
_DEFAULT_LENGTH = 16


def make_id(prefix: str, length: int = _DEFAULT_LENGTH) -> str:
    """Generate a prefixed unique ID.

    Args:
        prefix: Entity type prefix (e.g. "doc", "ovl", "evt", "cert")
        length: Random suffix length (default 16, ~95 bits entropy)

    Returns:
        String like "doc_K8mXp2nR4jW7qF9a"
    """
    suffix = "".join(secrets.choice(_ALPHABET) for _ in range(length))
    return f"{prefix}_{suffix}"
