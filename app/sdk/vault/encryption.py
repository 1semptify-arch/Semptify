"""
Vault encryption utilities for token backup and recovery.

These functions are separated from the VaultClient to keep the SDK focused
on storage operations only. Encryption is a cross-cutting concern used by
the Vault Installer for token backup creation.
"""

import json
import secrets
import hashlib
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class MasterToken:
    """
    Master token stored encrypted in user's cloud storage.
    This token NEVER leaves storage - server fetches and decrypts in-memory only.
    
    Contains:
    - Module authorizations (what features user can access)
    - OAuth credentials (access_token, refresh_token) as BACKUP
    
    The OAuth tokens in cloud are a BACKUP of the database tokens.
    This allows recovery if database is lost, and enables Rehome flow.
    """
    token_id: str                    # Unique token identifier
    user_id: str                     # User ID (GU2L3wyfBy format)
    created_at: str                  # ISO timestamp
    provider: str = ""               # Storage provider (google_drive, dropbox, onedrive)
    version: str = "5.0"             # Semptify version

    # OAuth credentials (backup - also stored in database for fast access)
    access_token: str = ""           # Provider OAuth access token
    refresh_token: str = ""          # Provider OAuth refresh token
    token_expires_at: str = ""       # When access_token expires

    # Module authorizations - which features this token unlocks
    modules: Optional[Dict[str, bool]] = None

    # Security
    last_validated: Optional[str] = None       # Last time token was used
    validation_count: int = 0        # How many times validated

    def __post_init__(self):
        if self.modules is None:
            self.modules = {
                "vault": True,
                "forms": True,
                "timeline": True,
                "copilot": True,
                "calendar": True,
                "defense": True,
                "zoom_court": True,
            }
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "MasterToken":
        return cls(**data)


def _derive_key(user_id: str, secret_key: str) -> bytes:
    """Derive encryption key from user_id + server secret."""
    combined = f"{secret_key}:token:{user_id}".encode()
    return hashlib.sha256(combined).digest()


def encrypt_token(token: MasterToken, user_id: str, secret_key: str) -> bytes:
    """
    Encrypt master token for storage with integrity verification.
    Uses AES-GCM which provides both encryption AND authentication (tamper detection).
    
    Args:
        token: MasterToken to encrypt
        user_id: User ID for key derivation
        secret_key: Server secret key for key derivation
    
    Returns:
        Encrypted bytes (nonce + ciphertext)
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from app.services.storage.legal_integrity import TokenIntegrity

    key = _derive_key(user_id, secret_key)
    nonce = secrets.token_bytes(12)
    
    # Wrap token with integrity hash before encryption
    wrapped = TokenIntegrity.wrap_token(token.to_dict(), user_id)
    plaintext = json.dumps(wrapped).encode()

    # AES-GCM provides authenticated encryption - any tampering will cause decryption to fail
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    return nonce + ciphertext


def decrypt_token(encrypted: bytes, user_id: str, secret_key: str) -> MasterToken:
    """
    Decrypt master token from storage with integrity verification.
    AES-GCM will raise InvalidTag if data was tampered with.
    
    Args:
        encrypted: Encrypted bytes (nonce + ciphertext)
        user_id: User ID for key derivation
        secret_key: Server secret key for key derivation
    
    Returns:
        Decrypted MasterToken
    
    Raises:
        ValueError: If decryption fails or token is invalid
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from app.services.storage.legal_integrity import TokenIntegrity

    key = _derive_key(user_id, secret_key)
    nonce = encrypted[:12]
    ciphertext = encrypted[12:]

    # AES-GCM decryption - will fail if tampered
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)

    wrapped = json.loads(plaintext.decode())
    
    # Handle both wrapped (with integrity) and legacy (without) formats
    if "integrity" in wrapped and "data" in wrapped:
        # New format with integrity verification
        TokenIntegrity.verify_token(wrapped, user_id)
        token_data = wrapped["data"]
    else:
        # Legacy format - no integrity verification
        token_data = wrapped
    
    return MasterToken.from_dict(token_data)
