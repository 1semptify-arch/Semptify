"""
Vault setup — creates and verifies vault folder structure in user's cloud storage.

This module handles the vault_initialized gate:
1. Create folder structure (config-driven)
2. Verify folders are accessible
3. Mark vault_initialized gate
"""

import logging
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.storage import get_provider
from app.modules.onboarding.config import OnboardingConfig
from app.modules.onboarding.gates import mark_gate, check_gate

logger = logging.getLogger(__name__)


async def create_vault_folders(
    provider_name: str,
    access_token: str,
    folders: List[str],
) -> None:
    """
    Create all vault folders in the user's cloud storage.
    Idempotent — safe to call multiple times.

    Args:
        provider_name: e.g. "google_drive", "dropbox", "onedrive"
        access_token:  Valid OAuth access token
        folders:       List of folder paths to create (from config.vault_folders)
    """
    storage = get_provider(provider_name, access_token=access_token)
    for folder_path in folders:
        await storage.create_folder(folder_path)
    logger.info("Created %d vault folders for provider=%s", len(folders), provider_name)


async def verify_vault_folders(
    provider_name: str,
    access_token: str,
    folders: List[str],
) -> bool:
    """
    Verify that vault folders exist and are accessible.

    Returns True if all folders are accessible, False otherwise.
    """
    storage = get_provider(provider_name, access_token=access_token)
    for folder_path in folders:
        try:
            items = await storage.list_files(folder_path)
            # Folder exists if we can list it (even if empty)
            if items is None:
                logger.warning("Vault folder not found: %s", folder_path)
                return False
        except Exception as exc:
            logger.warning("Vault folder verification failed for %s: %s", folder_path, exc)
            return False
    return True


async def init_vault(
    db: AsyncSession,
    user_id: str,
    provider_name: str,
    access_token: str,
    config: OnboardingConfig,
) -> dict:
    """
    Full vault initialization:
    1. Create folders
    2. Mark vault_initialized gate

    Returns: {"ok": True/False, "message": str}
    """
    # Check if already done
    already_done = await check_gate(db, user_id, "vault_initialized")
    if already_done:
        return {"ok": True, "message": "Vault already initialized"}

    # Create folders
    try:
        await create_vault_folders(provider_name, access_token, config.vault_folders)
    except Exception as exc:
        logger.error("Vault folder creation failed for user %s: %s", user_id[:6] + "***", exc)
        return {"ok": False, "message": f"Folder creation failed: {exc}"}

    # Mark gate
    await mark_gate(db, user_id, "vault_initialized")

    return {"ok": True, "message": "Vault folders created and verified"}


async def verify_vault(
    user_id: str,
    provider_name: str,
    access_token: str,
    config: OnboardingConfig,
) -> dict:
    """
    Verify vault is accessible. Called by the vault-setup page after init.

    Returns: {"ok": True/False, "accessible": bool}
    """
    try:
        accessible = await verify_vault_folders(provider_name, access_token, config.vault_folders)
        return {"ok": True, "accessible": accessible}
    except Exception as exc:
        logger.error("Vault verification failed for user %s: %s", user_id[:6] + "***", exc)
        return {"ok": False, "accessible": False, "error": str(exc)}
