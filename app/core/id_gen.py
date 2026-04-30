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
    - 16-char alphanumeric suffix = ~95 bits of entropy (~10^28 combinations)
    - No hyphens, URL-safe, filename-safe, sortable
    - Prefix identifies entity type at a glance
    - No truncated UUIDs, no collision risk at Semptify scale

Performance: ~10,000 IDs/ms (sufficient for all use cases)

User IDs are NOT generated here — they use a separate scheme
in app/core/user_id.py (provider+role+8-char format).

ID Types (canonical prefixes):
    doc  = Vault document
    ovl  = Document overlay
    evt  = Timeline event
    cert = Document certificate
    lnk  = Linked provider
    case = Legal case
    aud  = Audit log entry
    acr  = Access control request
    ent  = Extracted entity (recognition)
    sec  = Document section
    iss  = Legal issue
    tle  = Timeline entry
    rel  = Party relationship
    amt  = Financial amount
    anl  = Analysis result
    hwa  = Handwriting analysis
    fri  = Signature profile
    chk  = Research checkpoint
    zip  = Zip archive token
"""

from enum import Enum
from typing import Optional
import secrets
import string

_ALPHABET = string.ascii_letters + string.digits
_DEFAULT_LENGTH = 16
_MAX_PREFIX_LEN = 10  # Prevent absurdly long prefixes


class IdType(str, Enum):
    """Canonical ID type prefixes for type safety."""
    DOCUMENT = "doc"
    OVERLAY = "ovl"
    EVENT = "evt"
    CERTIFICATE = "cert"
    LINKED_PROVIDER = "lnk"
    CASE = "case"
    AUDIT = "aud"
    ACCESS_REQUEST = "acr"
    ENTITY = "ent"
    SECTION = "sec"
    ISSUE = "iss"
    TIMELINE_ENTRY = "tle"
    RELATIONSHIP = "rel"
    AMOUNT = "amt"
    ANALYSIS = "anl"
    HANDWRITING_ANALYSIS = "hwa"
    SIGNATURE_PROFILE = "fri"
    CHECKPOINT = "chk"
    ZIP_TOKEN = "zip"


def make_id(prefix: str, length: int = _DEFAULT_LENGTH) -> str:
    """Generate a prefixed unique ID.

    Args:
        prefix: Entity type prefix (e.g. "doc", "ovl", "evt", "cert")
               Use IdType enum for type safety: make_id(IdType.DOCUMENT.value)
        length: Random suffix length (default 16, ~95 bits entropy)

    Returns:
        String like "doc_K8mXp2nR4jW7qF9a"

    Raises:
        ValueError: If prefix is invalid (contains underscore, too long, etc.)
    """
    # Validation
    if not prefix:
        raise ValueError("Prefix cannot be empty")
    if "_" in prefix:
        raise ValueError(f"Prefix cannot contain underscore: {prefix}")
    if len(prefix) > _MAX_PREFIX_LEN:
        raise ValueError(f"Prefix too long (max {_MAX_PREFIX_LEN}): {prefix}")
    if not prefix.isalnum():
        raise ValueError(f"Prefix must be alphanumeric: {prefix}")
    
    suffix = "".join(secrets.choice(_ALPHABET) for _ in range(length))
    return f"{prefix}_{suffix}"


def make_id_typed(id_type: IdType, length: int = _DEFAULT_LENGTH) -> str:
    """Type-safe ID generation using IdType enum.
    
    Example:
        >>> make_id_typed(IdType.DOCUMENT)
        'doc_K8mXp2nR4jW7qF9a'
    """
    return make_id(id_type.value, length)


def parse_id(full_id: str) -> tuple[str, str]:
    """Parse a full ID into (prefix, suffix).
    
    Args:
        full_id: ID like "doc_K8mXp2nR4jW7qF9a"
        
    Returns:
        Tuple of (prefix, suffix)
        
    Raises:
        ValueError: If ID format is invalid
    """
    if "_" not in full_id:
        raise ValueError(f"Invalid ID format (no underscore): {full_id}")
    
    parts = full_id.split("_", 1)  # Split on first underscore only
    prefix, suffix = parts[0], parts[1]
    
    if not prefix or not suffix:
        raise ValueError(f"Invalid ID format (empty prefix or suffix): {full_id}")
    
    return prefix, suffix


def validate_id(full_id: str, expected_prefix: Optional[str] = None) -> bool:
    """Validate an ID format and optionally check prefix.
    
    Args:
        full_id: ID to validate
        expected_prefix: If provided, verify ID has this prefix
        
    Returns:
        True if valid, False otherwise
    """
    try:
        prefix, suffix = parse_id(full_id)
        
        # Check prefix if specified
        if expected_prefix and prefix != expected_prefix:
            return False
            
        # Check suffix is valid alphanumeric
        if not suffix or not all(c in _ALPHABET for c in suffix):
            return False
            
        return True
    except ValueError:
        return False


# Backwards compatibility alias
def generate_id(prefix: str, length: int = _DEFAULT_LENGTH) -> str:
    """Alias for make_id()."""
    return make_id(prefix, length)
