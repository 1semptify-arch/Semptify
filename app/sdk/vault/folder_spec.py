"""
Declarative vault folder specifications.

ALL paths import from app/core/vault_paths.py — the single source of truth.
This file never defines its own path strings. Products extend the base spec
with additional folders using vault_paths constants.
"""

from dataclasses import dataclass

from app.core.vault_paths import (
    AUTH_FOLDER,
    SEMPTIFY_ROOT,
    SYSTEM_FOLDER,
    VAULT_CERTIFICATES,
    VAULT_DOCUMENTS,
    VAULT_FOLDER,
    VAULT_ROOT,
)


@dataclass(frozen=True)
class VaultFolderSpec:
    """
    Declarative vault folder structure.

    Two layers:
      1. base_folders — Universal. Created by SDK for every Semptify product.
         Identity, auth, vault root. Nobody touches these.
      2. product_folders — Product-specific. Each product registers its own.
         Tenant adds "documents". Advocate adds "legal_filings". Etc.

    Products ONLY interact with product_folders. The base is invisible to them.
    """

    root: str = SEMPTIFY_ROOT

    base_folders: tuple = (
        SEMPTIFY_ROOT,
        VAULT_ROOT,
        SYSTEM_FOLDER,
        AUTH_FOLDER,
        VAULT_FOLDER,
    )

    product_folders: tuple = ()

    @property
    def all_folders(self) -> list[str]:
        """All folders that should exist, in creation order (base + product)."""
        return list(self.base_folders) + list(self.product_folders)

    def extend(self, folders: list[str]) -> "VaultFolderSpec":
        """Return a new spec with additional product-specific folders."""
        return VaultFolderSpec(
            root=self.root,
            base_folders=self.base_folders,
            product_folders=self.product_folders + tuple(folders),
        )


# ============================================================================
# Universal base — what every Semptify product gets automatically.
# SDK creates this. Products never think about it.
# ============================================================================

BASE_VAULT = VaultFolderSpec()


# ============================================================================
# Product specs — each product adds ONLY its own subfolders.
# ============================================================================

TENANT_VAULT = BASE_VAULT.extend([
    VAULT_DOCUMENTS,
    VAULT_CERTIFICATES,
])

ADVOCATE_VAULT = BASE_VAULT.extend([
    VAULT_DOCUMENTS,
    f"{VAULT_ROOT}/client_files",
    f"{VAULT_ROOT}/case_notes",
    f"{VAULT_ROOT}/legal_filings",
])

LEGAL_VAULT = BASE_VAULT.extend([
    VAULT_DOCUMENTS,
    f"{VAULT_ROOT}/court_exhibits",
    f"{VAULT_ROOT}/case_files",
    f"{VAULT_ROOT}/discovery",
])

RESEARCH_VAULT = BASE_VAULT.extend([
    f"{VAULT_ROOT}/research",
    f"{VAULT_ROOT}/dossiers",
])
