"""
Semptify Auth SDK — Token Primitives
=====================================
Hashing, HMAC signing, token generation.
Zero framework dependencies. Pure Python.
"""

import hashlib
import hmac
import secrets
import string
from typing import Optional


def hash_token(token: str) -> str:
    """SHA-256 hash a token for safe storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_token(length: int = 12, digits_only: bool = True) -> str:
    """Generate a cryptographically secure random token."""
    alphabet = string.digits if digits_only else string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def sign_value(value: str, secret: str) -> str:
    """HMAC-sign a value with a secret key. Returns 'value.signature'."""
    sig = hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{value}.{sig}"


def verify_signed_value(signed: str, secret: str) -> Optional[str]:
    """
    Verify an HMAC-signed value.
    Returns the original value if valid, None if tampered.
    """
    if "." not in signed:
        return None
    value, sig = signed.rsplit(".", 1)
    expected_sig = hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()[:16]
    if hmac.compare_digest(sig, expected_sig):
        return value
    return None


def verify_hmac_user_id(signed_user_id: str, secret: str) -> Optional[str]:
    """
    Verify an HMAC-signed user ID cookie value.
    Returns the raw user_id if valid, None if invalid.
    """
    return verify_signed_value(signed_user_id, secret)
