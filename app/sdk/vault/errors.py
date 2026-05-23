"""
import logging
logger = logging.getLogger(__name__)
Vault SDK error hierarchy.

All vault-specific errors inherit from VaultError so callers can
catch broadly or narrowly.
"""


class VaultError(Exception):
    """Base error for all vault operations."""


class VaultProviderError(VaultError):
    """Storage provider failed (API error, auth expired, rate limit)."""


class VaultFolderError(VaultError):
    """Folder creation or verification failed."""


class VaultTokenError(VaultError):
    """Master token read/write/decrypt failed."""
