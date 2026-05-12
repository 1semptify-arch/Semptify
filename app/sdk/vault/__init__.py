"""
Semptify Vault SDK
==================

Isolated, reusable vault management for any Semptify product.

Usage:
    from app.sdk.vault import VaultClient, TENANT_VAULT

    vault = VaultClient(
        provider="google_drive",
        access_token="ya29.xxxxx",
        user_id="GU2L3wyfBy",
    )
    result = await vault.create_folders()

No database, no FastAPI, no middleware dependencies.
"""

__version__ = "1.0.0"

from app.sdk.vault.client import VaultClient
from app.sdk.vault.folder_spec import (
    VaultFolderSpec,
    TENANT_VAULT,
    ADVOCATE_VAULT,
    LEGAL_VAULT,
    RESEARCH_VAULT,
)
from app.sdk.vault.errors import (
    VaultError,
    VaultProviderError,
    VaultFolderError,
    VaultTokenError,
)

__all__ = [
    "VaultClient",
    "VaultFolderSpec",
    "TENANT_VAULT",
    "ADVOCATE_VAULT",
    "LEGAL_VAULT",
    "RESEARCH_VAULT",
    "VaultError",
    "VaultProviderError",
    "VaultFolderError",
    "VaultTokenError",
]
