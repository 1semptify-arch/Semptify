"""Canonical key derivation — the ONLY place SECRET_KEY is mixed.

Semptify derives every encryption/signing key from the server SECRET_KEY
plus a user_id. Before this module existed, that mixing lived in four
separate places and silently disagreed:

- ``cookie_auth.py``          — HMAC(secret, user_id)         (cookie signing)
- ``storage/router.py``       — sha256(secret:user_id)        (session tokens, write)
- ``auto_refresh.py``         — sha256(secret:user_id)        (session tokens, read)
- ``sdk/vault/encryption.py`` — sha256(secret:token:user_id)  (MasterToken cloud backup)

This module is the single source for all four. The formulas are
**byte-identical to the legacy implementations** — existing rows and cookies
must keep working — but each is now an explicit ``purpose`` label so the
":token:" separator is intentional domain separation, not an accident.

Versioning (spec: handoffs/vault-security-pair-spec-2026-09-06.md, Scope A):

- ``SECRET_KEY``         — the current secret (env, as today)
- ``SECRET_KEY_VERSION`` — integer version of the current secret (default 0)
- ``SECRET_KEY_HISTORY`` — JSON list of retired keys, each
  ``{"version": int, "key": str, "rotated_at": "<iso8601>"}``

Reads fall back through valid history entries (60-day grace from
``rotated_at``); writes always use the current key. After the grace window a
history entry stops verifying — sessions then reconnect via the existing
``/storage/reconnect`` flow.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Iterator

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Purposes — explicit domain separation between the three AES/HMAC uses.
PURPOSE_SESSION_TOKEN = "session-token"  # sessions table access/refresh tokens
PURPOSE_MASTER_TOKEN = "master-token"    # MasterToken backup in user's cloud
PURPOSE_COOKIE = "cookie"                # semptify_uid cookie HMAC

GRACE_PERIOD_DAYS = 60


# ---------------------------------------------------------------------------
# Secret material — current + versioned history
# ---------------------------------------------------------------------------

def _current_secret() -> str:
    settings = get_settings()
    return getattr(settings, "secret_key", None) or getattr(settings, "SECRET_KEY", "")


def current_key_version() -> int:
    """Version stamp written to rows encrypted right now."""
    explicit = int(getattr(get_settings(), "secret_key_version", 0) or 0)
    if explicit:
        return explicit
    history = _history_entries()
    return (max(e["version"] for e in history) + 1) if history else 0


def _history_entries() -> list[dict]:
    """Parse SECRET_KEY_HISTORY. Malformed entries are skipped, not fatal."""
    raw = getattr(get_settings(), "secret_key_history", "") or ""
    if not raw.strip():
        return []
    try:
        entries = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        logger.warning("SECRET_KEY_HISTORY is not valid JSON — history disabled")
        return []
    valid: list[dict] = []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict) or "key" not in entry:
            continue
        valid.append(
            {
                "version": int(entry.get("version", 0)),
                "key": str(entry["key"]),
                "rotated_at": entry.get("rotated_at"),
            }
        )
    # Newest-first so the most recent key is tried before older ones.
    valid.sort(key=lambda e: e["version"], reverse=True)
    return valid


def _in_grace(entry: dict) -> bool:
    """A history entry verifies for GRACE_PERIOD_DAYS after its rotated_at."""
    rotated_at = entry.get("rotated_at")
    if not rotated_at:
        return True  # no timestamp — grandfathered, operator manages removal
    try:
        rotated = datetime.fromisoformat(str(rotated_at).replace("Z", "+00:00"))
        if rotated.tzinfo is None:
            rotated = rotated.replace(tzinfo=UTC)
        return datetime.now(UTC) - rotated <= timedelta(days=GRACE_PERIOD_DAYS)
    except ValueError:
        logger.warning("SECRET_KEY_HISTORY entry has bad rotated_at: %r", rotated_at)
        return False


def iter_valid_secrets() -> Iterator[tuple[int, str]]:
    """Yield (version, secret): current first, then in-grace history."""
    yield current_key_version(), _current_secret()
    for entry in _history_entries():
        if _in_grace(entry):
            yield entry["version"], entry["key"]


def _secret_for_version(version: int) -> str | None:
    """The secret for an explicit version, or None if retired/expired."""
    if version == current_key_version():
        return _current_secret()
    for entry in _history_entries():
        if entry["version"] == version and _in_grace(entry):
            return entry["key"]
    return None


# ---------------------------------------------------------------------------
# AES key derivation — byte-identical to the legacy formulas
# ---------------------------------------------------------------------------

def derive_key_material(secret: str, user_id: str, purpose: str) -> bytes:
    """Mix an explicit secret + user_id into a 32-byte key for a purpose.

    This is the single place key material is combined — call sites that carry
    their own secret (e.g. the vault SDK) go through here so the formula can
    never drift.
    """
    if purpose == PURPOSE_MASTER_TOKEN:
        combined = f"{secret}:token:{user_id}".encode()
    elif purpose == PURPOSE_SESSION_TOKEN:
        combined = f"{secret}:{user_id}".encode()
    else:
        raise ValueError(f"Unknown key purpose: {purpose!r}")
    return hashlib.sha256(combined).digest()


def derive_key(user_id: str, purpose: str = PURPOSE_SESSION_TOKEN, key_version: int | None = None) -> bytes:
    """Derive a 32-byte AES key. ``key_version=None`` → current version."""
    if key_version is None:
        secret = _current_secret()
    else:
        secret = _secret_for_version(key_version)
        if secret is None:
            raise ValueError(f"No valid secret for key_version {key_version}")
    return derive_key_material(secret, user_id, purpose)


def _candidate_versions(hint: int | None) -> list[int]:
    """Ordered versions to try: hint first (if valid), then current, then history."""
    versions = [v for v, _ in iter_valid_secrets()]
    ordered: list[int] = []
    if hint is not None and hint in versions:
        ordered.append(hint)
    ordered += [v for v in versions if v != hint]
    return ordered


# ---------------------------------------------------------------------------
# String encrypt/decrypt — session tokens (AES-256-GCM, base64 wire format)
# ---------------------------------------------------------------------------

def encrypt_value(value: str, user_id: str) -> str:
    """Encrypt a string with the CURRENT key. Returns base64(nonce+ct)."""
    import secrets

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = derive_key(user_id, PURPOSE_SESSION_TOKEN)
    nonce = secrets.token_bytes(12)
    plaintext = json.dumps({"v": value}).encode()
    return base64.b64encode(nonce + AESGCM(key).encrypt(nonce, plaintext, None)).decode("utf-8")


def decrypt_value(encrypted: str, user_id: str, key_version: int | None = None) -> str:
    """Decrypt a base64 encrypted string.

    ``key_version`` is the row's stored version (hint first); when unknown
    (legacy NULL rows) every valid version is tried. Raises on total failure —
    callers treat that as a corrupt/expired-credential signal, exactly as
    before.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    raw = base64.b64decode(encrypted.encode("utf-8"))
    nonce, ciphertext = raw[:12], raw[12:]

    last_error: Exception | None = None
    for version in _candidate_versions(key_version):
        secret = _secret_for_version(version)
        if secret is None:
            continue
        key = derive_key_material(secret, user_id, PURPOSE_SESSION_TOKEN)
        try:
            plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
            return json.loads(plaintext.decode())["v"]
        except Exception as e:  # InvalidTag + parse errors — try next version
            last_error = e
    raise ValueError(f"Could not decrypt value with any valid key version: {last_error}")


# ---------------------------------------------------------------------------
# Cookie HMAC — sign with current, verify against current + valid history
# ---------------------------------------------------------------------------

def hmac_sign_user_id(user_id: str) -> str:
    """HMAC-SHA256 signature over user_id with the current secret."""
    return hmac.new(_current_secret().encode("utf-8"), user_id.encode("utf-8"), hashlib.sha256).hexdigest()


def hmac_verify_user_id(user_id: str, provided_sig: str) -> bool:
    """Constant-time verify; tries current key then valid history."""
    for _version, secret in iter_valid_secrets():
        expected = hmac.new(secret.encode("utf-8"), user_id.encode("utf-8"), hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected, provided_sig):
            return True
    return False
