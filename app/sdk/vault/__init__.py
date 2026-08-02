"""
Vault SDK - Isolated, reusable vault management for all Semptify products.

Zero dependencies on FastAPI, SQLAlchemy, middleware, or navigation.
Takes a provider name, access token, and user ID. Does storage operations.

Usage:
    from app.sdk.vault import VaultClient, TENANT_VAULT
import logging
logger = logging.getLogger(__name__)

    vault = VaultClient(
        provider="google_drive",
        access_token="ya29.xxxxx",
        user_id="GU2L3wyfBy",
        folder_spec=TENANT_VAULT,
    )
    result = await vault.create_folders()
"""

__version__ = "1.0.0"

from app.sdk.vault.client import VaultClient, VaultResult
from app.sdk.vault.encryption import (
    MasterToken,
    decrypt_token,
    encrypt_token,
)
from app.sdk.vault.errors import (
    VaultError,
    VaultFolderError,
    VaultProviderError,
    VaultTokenError,
)
from app.sdk.vault.folder_spec import (
    ADVOCATE_VAULT,
    BASE_VAULT,
    LEGAL_VAULT,
    RESEARCH_VAULT,
    TENANT_VAULT,
    VaultFolderSpec,
)

__all__ = [
    "VaultClient",
    "VaultFolderSpec",
    "BASE_VAULT",
    "TENANT_VAULT",
    "ADVOCATE_VAULT",
    "LEGAL_VAULT",
    "RESEARCH_VAULT",
    "VaultError",
    "VaultProviderError",
    "VaultFolderError",
    "VaultTokenError",
    "VaultResult",
    "MasterToken",
    "encrypt_token",
    "decrypt_token",
]
