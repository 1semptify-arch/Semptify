"""
Semptify Vault Installer

Library that creates the Semptify vault structure directly in the user's
OAuth-authorized storage provider. Used by the canonical onboarding
vault-setup flow at /onboarding/api/vault/*.

The duplicate /api/vault-installer/* HTTP surface was removed 2026-09-21 —
/onboarding/api/vault/* is the single entry point (SSOT "one way in").
"""

import logging

from .installer import VaultInstaller, install_vault_folders_only, install_vault_for_user

logger = logging.getLogger(__name__)

__all__ = [
    "VaultInstaller",
    "install_vault_for_user",
    "install_vault_folders_only",
]
