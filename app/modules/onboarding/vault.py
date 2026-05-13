"""
Vault setup — creates folder structure, places system files, and verifies
write+read access in the user's cloud storage.

This module handles the vault_initialized gate:
1. Create folder structure (config-driven)
2. Place system files (Rehome, README, vault manifest)
3. Read-back verification (prove the provider accepted writes)
4. Mark vault_initialized gate (only after verified)
"""

import json
import logging
from datetime import datetime, timezone
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.storage import get_provider
from app.modules.onboarding.config import OnboardingConfig
from app.modules.onboarding.gates import mark_gate, check_gate
from app.core.vault_paths import SEMPTIFY_ROOT, VAULT_FOLDER

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Folder operations
# ---------------------------------------------------------------------------

async def create_vault_folders(
    provider_name: str,
    access_token: str,
    folders: List[str],
) -> None:
    """
    Create all vault folders in the user's cloud storage.
    Idempotent — safe to call multiple times.
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
            if items is None:
                logger.warning("Vault folder not found: %s", folder_path)
                return False
        except Exception as exc:
            logger.warning("Vault folder verification failed for %s: %s", folder_path, exc)
            return False
    return True


# ---------------------------------------------------------------------------
# System file provisioning
# ---------------------------------------------------------------------------

async def _place_system_files(
    provider_name: str,
    access_token: str,
    user_id: str,
    base_url: str,
) -> List[dict]:
    """
    Write the system files that every vault needs:
      - Rehome.html       → Semptify5.0/         (device reconnection)
      - README.txt         → Semptify5.0/         (DO NOT DELETE notice)
      - vault_manifest.json → .Semptify5.0/vault/ (completion proof + system check)

    Returns list of {"type": "file", "path": str} for each file placed.
    """
    from app.services.storage.vault_manager import (
        generate_rehome_html,
        generate_readme,
    )

    storage = get_provider(provider_name, access_token=access_token)
    placed = []

    # --- Rehome.html ---
    rehome_html = generate_rehome_html(user_id, provider_name, base_url)
    await storage.upload_file(
        file_content=rehome_html.encode(),
        destination_path=SEMPTIFY_ROOT,
        filename="Rehome.html",
        mime_type="text/html",
    )
    placed.append({"type": "file", "path": f"{SEMPTIFY_ROOT}/Rehome.html"})

    # --- README.txt ---
    readme = generate_readme()
    await storage.upload_file(
        file_content=readme.encode(),
        destination_path=SEMPTIFY_ROOT,
        filename="README.txt",
        mime_type="text/plain",
    )
    placed.append({"type": "file", "path": f"{SEMPTIFY_ROOT}/README.txt"})

    # --- vault_manifest.json (system check file) ---
    manifest = {
        "semptify_version": "5.0",
        "user_id": user_id,
        "provider": provider_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "vault_status": "active",
    }
    manifest_bytes = json.dumps(manifest, indent=2).encode()
    await storage.upload_file(
        file_content=manifest_bytes,
        destination_path=VAULT_FOLDER,
        filename="manifest.json",
        mime_type="application/json",
    )
    placed.append({"type": "file", "path": f"{VAULT_FOLDER}/manifest.json"})

    logger.info("Placed %d system files for user %s", len(placed), user_id[:6] + "***")
    return placed


# ---------------------------------------------------------------------------
# Read-back verification
# ---------------------------------------------------------------------------

async def _verify_system_check(
    provider_name: str,
    access_token: str,
    user_id: str,
) -> bool:
    """
    Read back the vault manifest and confirm the content is valid.
    This proves the provider accepted the write AND the data is retrievable.
    """
    storage = get_provider(provider_name, access_token=access_token)
    manifest_path = f"{VAULT_FOLDER}/manifest.json"

    try:
        content = await storage.download_file(manifest_path)
        data = json.loads(content.decode())
        if data.get("user_id") != user_id:
            logger.error(
                "Vault manifest read-back: user_id mismatch (expected %s, got %s)",
                user_id[:6] + "***", str(data.get("user_id", ""))[:6] + "***",
            )
            return False
        if data.get("vault_status") != "active":
            logger.error("Vault manifest read-back: vault_status is not 'active'")
            return False
        logger.info("Vault manifest read-back verified for user %s", user_id[:6] + "***")
        return True
    except Exception as exc:
        logger.error("Vault manifest read-back failed for user %s: %s", user_id[:6] + "***", exc)
        return False


# ---------------------------------------------------------------------------
# Main entry points
# ---------------------------------------------------------------------------

async def init_vault(
    db: AsyncSession,
    user_id: str,
    provider_name: str,
    access_token: str,
    config: OnboardingConfig,
    base_url: str = "",
) -> dict:
    """
    Full vault initialization:
    1. Create folders
    2. Place system files (Rehome, README, vault manifest)
    3. Read-back verification (prove provider accepted writes)
    4. Mark vault_initialized gate (only after verified)

    Args:
        base_url: Public Semptify URL for Rehome script. Falls back to settings.

    Returns: {"ok": True/False, "message": str}
    """
    # Check if already done
    already_done = await check_gate(db, user_id, "vault_initialized")
    if already_done:
        return {"ok": True, "message": "Vault already initialized"}

    # Resolve base_url if not provided
    if not base_url:
        try:
            from app.core.config import get_settings
            settings = get_settings()
            base_url = (settings.public_base_url or "https://semptify.com").rstrip("/")
        except Exception:
            base_url = "https://semptify.com"

    # 1. Create folders
    try:
        await create_vault_folders(provider_name, access_token, config.vault_folders)
    except Exception as exc:
        logger.error("Vault folder creation failed for user %s: %s", user_id[:6] + "***", exc)
        return {"ok": False, "message": f"Folder creation failed: {exc}"}

    # 2. Place system files
    try:
        await _place_system_files(provider_name, access_token, user_id, base_url)
    except Exception as exc:
        logger.error("System file provisioning failed for user %s: %s", user_id[:6] + "***", exc)
        return {"ok": False, "message": f"System file provisioning failed: {exc}"}

    # 3. Read-back verification
    verified = await _verify_system_check(provider_name, access_token, user_id)
    if not verified:
        return {"ok": False, "message": "Vault write+read verification failed — storage may not be accepting writes"}

    # 4. Mark gate — vault creation IS activation
    await mark_gate(db, user_id, "vault_initialized")

    return {"ok": True, "message": "Vault created, provisioned, and verified"}


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
