"""
Semptify Vault Installer

A standalone installer that creates the Semptify vault structure
directly in the user's OAuth-authorized storage provider.

No complex onboarding flow - just install the vault and activate.
"""

from .installer import VaultInstaller, install_vault_for_user, install_vault_folders_only
from .routes import create_router
from .register import register_vault_installer

__all__ = ["VaultInstaller", "install_vault_for_user", "install_vault_folders_only", "create_router", "register_vault_installer"]
