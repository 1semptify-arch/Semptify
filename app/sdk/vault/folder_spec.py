"""
Declarative vault folder specifications.

ALL paths import from app/core/vault_paths.py — the single source of truth.
This file never defines its own path strings. Products extend the base spec
with additional folders using vault_paths constants.
"""

from dataclasses import dataclass, field
from typing import List

from app.core.vault_paths import (
    SEMPTIFY_ROOT,
    AUTH_FOLDER,
    VAULT_FOLDER,
    VAULT_ROOT,
    VAULT_DOCUMENTS,
    VAULT_CERTIFICATES,
    VAULT_TIMELINE,
    VAULT_OVERLAYS,
)


@dataclass(frozen=True)
class VaultFolderSpec:
    """
    Declarative vault folder structure.

    Attributes:
        root:            Top-level folder name. From vault_paths.SEMPTIFY_ROOT.
        core_folders:    Always created for every product. From vault_paths.
        auth_folders:    Hidden auth/metadata folders. From vault_paths.
        product_folders: Additional folders specific to a product.
    """

    root: str = SEMPTIFY_ROOT

    core_folders: tuple = (
        SEMPTIFY_ROOT,
        VAULT_ROOT,
        VAULT_DOCUMENTS,
        VAULT_CERTIFICATES,
    )

    auth_folders: tuple = (
        AUTH_FOLDER,
        VAULT_FOLDER,
    )

    product_folders: tuple = ()

    @property
    def all_folders(self) -> List[str]:
        """All folders that should exist, in creation order."""
        return list(self.core_folders) + list(self.auth_folders) + list(self.product_folders)

    def extend(self, folders: List[str]) -> "VaultFolderSpec":
        """Return a new spec with additional product-specific folders."""
        return VaultFolderSpec(
            root=self.root,
            core_folders=self.core_folders,
            auth_folders=self.auth_folders,
            product_folders=self.product_folders + tuple(folders),
        )


# ============================================================================
# Pre-built specs for each Semptify product
# ============================================================================

TENANT_VAULT = VaultFolderSpec()

ADVOCATE_VAULT = VaultFolderSpec(product_folders=(
    f"{VAULT_ROOT}/client_files",
    f"{VAULT_ROOT}/case_notes",
    f"{VAULT_ROOT}/legal_filings",
))

LEGAL_VAULT = VaultFolderSpec(product_folders=(
    f"{VAULT_ROOT}/court_exhibits",
    f"{VAULT_ROOT}/case_files",
    f"{VAULT_ROOT}/discovery",
))

RESEARCH_VAULT = VaultFolderSpec(product_folders=(
    f"{VAULT_ROOT}/research",
    f"{VAULT_ROOT}/dossiers",
))
