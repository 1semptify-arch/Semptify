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
from app.utils.utc_now import utc_now
from app.core.vault_paths import (
    SEMPTIFY_ROOT,
    VAULT_FOLDER,
    AUTH_FOLDER,
    VAULT_DOCUMENTS,
    VAULT_TIMELINE,
    VAULT_TIMELINE_EVENTS_FILENAME,
    VAULT_OVERLAYS,
    VAULT_OVERLAY_REGISTRY,
)

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

    Raises RuntimeError if any folder cannot be created.
    """
    storage = get_provider(provider_name, access_token=access_token)
    for folder_path in folders:
        ok = await storage.create_folder(folder_path)
        if not ok:
            raise RuntimeError(
                f"Provider {provider_name} refused to create folder: {folder_path}"
            )
        logger.info("Vault folder ensured: %s", folder_path)
    logger.info("Created %d vault folders for provider=%s", len(folders), provider_name)


async def verify_vault_folders(
    provider_name: str,
    access_token: str,
    folders: List[str],
) -> bool:
    """
    Verify that vault folders exist and are accessible.
    Returns True if all folders are accessible, False otherwise.

    NOTE: Empty folders are OK after init (documents/, certificates/ have no
    files yet). Only fail if list_files throws, which means the folder path
    is not accessible.
    """
    storage = get_provider(provider_name, access_token=access_token)
    for folder_path in folders:
        try:
            # list_files throws if the folder path is not accessible.
            # An empty list [] means the folder exists but has no items —
            # this is expected for documents/ and certificates/ before upload.
            await storage.list_files(folder_path)
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


async def _initialize_vault_data_files(
    provider_name: str,
    access_token: str,
    user_id: str,
) -> List[dict]:
    """
    Initialize empty data files that Semptify products expect:
      - timeline/events.json          → empty array (event log)
      - overlays/registry.json        → empty object (overlay index)

    These are created once during onboarding so downstream code
    never has to handle "file does not exist" race conditions.
    """
    storage = get_provider(provider_name, access_token=access_token)
    placed = []

    # --- timeline/events.json ---
    events_data = {"events": [], "version": "1.0", "created_by": user_id}
    await storage.upload_file(
        file_content=json.dumps(events_data, indent=2).encode(),
        destination_path=VAULT_TIMELINE,
        filename=VAULT_TIMELINE_EVENTS_FILENAME,
        mime_type="application/json",
    )
    placed.append({"type": "data_file", "path": f"{VAULT_TIMELINE}/{VAULT_TIMELINE_EVENTS_FILENAME}"})

    # --- overlays/registry.json ---
    registry_data = {
        "version": "1.0",
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "overlays": {},
    }
    await storage.upload_file(
        file_content=json.dumps(registry_data, indent=2).encode(),
        destination_path=VAULT_OVERLAYS,
        filename="registry.json",
        mime_type="application/json",
    )
    placed.append({"type": "data_file", "path": f"{VAULT_OVERLAY_REGISTRY}"})

    logger.info(
        "Initialized %d vault data files for user %s", len(placed), user_id[:6] + "***"
    )
    return placed


# ---------------------------------------------------------------------------
# Encrypted token backup
# ---------------------------------------------------------------------------

async def _store_encrypted_token_backup(
    provider_name: str,
    access_token: str,
    user_id: str,
) -> None:
    """
    Encrypt the OAuth token and store it as a backup in .auth/.

    Files written:
      - .Semptify5.0/auth/token.enc         (primary)
      - .Semptify5.0/auth/token.enc.backup   (redundant copy)
      - .Semptify5.0/auth/device_keys.json   (authorized devices list)

    The encrypted backup allows token recovery via Rehome if the
    database is lost. Uses AES-GCM from vault_manager helpers.
    """
    from app.services.storage.vault_manager import (
        MasterToken,
        encrypt_token,
        decrypt_token,
    )
    import secrets as _secrets

    storage = get_provider(provider_name, access_token=access_token)

    # Build master token with current OAuth credentials
    token = MasterToken(
        token_id=_secrets.token_urlsafe(32),
        user_id=user_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        provider=provider_name,
        access_token=access_token,
    )

    encrypted = encrypt_token(token, user_id)

    # Write primary + backup
    await storage.upload_file(
        file_content=encrypted,
        destination_path=AUTH_FOLDER,
        filename="token.enc",
        mime_type="application/octet-stream",
    )
    await storage.upload_file(
        file_content=encrypted,
        destination_path=AUTH_FOLDER,
        filename="token.enc.backup",
        mime_type="application/octet-stream",
    )

    # Verify the primary can be read back and decrypted
    from app.core.vault_paths import TOKEN_FILE
    read_back = await storage.download_file(TOKEN_FILE)
    decrypted = decrypt_token(read_back, user_id)
    if decrypted.user_id != user_id:
        raise ValueError("Token backup read-back: user_id mismatch after decrypt")

    # Initialize empty device keys
    device_keys = {"devices": [], "created_at": utc_now().isoformat()}
    await storage.upload_file(
        file_content=json.dumps(device_keys, indent=2).encode(),
        destination_path=AUTH_FOLDER,
        filename="device_keys.json",
        mime_type="application/json",
    )

    logger.info("Encrypted token backup stored for user %s", user_id[:6] + "***")


# ---------------------------------------------------------------------------
# Read-back verification
# ---------------------------------------------------------------------------

async def _verify_system_check(
    provider_name: str,
    access_token: str,
    user_id: str,
    config: OnboardingConfig,
) -> dict:
    """
    Comprehensive system test — proves the vault is fully operational:

    1. Folder accessibility: list_files() on every vault folder
    2. Write test: upload a temporary file to the documents folder
    3. Read test: download the temporary file back
    4. Delete test: remove the temporary file
    5. System file integrity: manifest.json, events.json, registry.json

    Returns {"ok": bool, "message": str, "details": list}.
    """
    import secrets as _secrets

    storage = get_provider(provider_name, access_token=access_token)
    details = []

    # --- 1. Folder accessibility ---
    for folder_path in config.vault_folders:
        try:
            await storage.list_files(folder_path)
            details.append(f"folder_accessible: {folder_path}")
        except Exception as exc:
            logger.error("Folder access failed for %s: %s", folder_path, exc)
            return {
                "ok": False,
                "message": f"Folder not accessible: {folder_path}",
                "details": details,
            }

    # --- 2. Write test ---
    test_filename = f"_system_test_{_secrets.token_hex(4)}.txt"
    test_content = f"Semptify vault system test | user={user_id} | ts={datetime.now(timezone.utc).isoformat()}".encode()
    try:
        await storage.upload_file(
            file_content=test_content,
            destination_path=VAULT_DOCUMENTS,
            filename=test_filename,
            mime_type="text/plain",
        )
        details.append(f"write_test: uploaded {test_filename}")
    except Exception as exc:
        logger.error("Write test failed for user %s: %s", user_id[:6] + "***", exc)
        return {"ok": False, "message": f"Write test failed: {exc}", "details": details}

    # --- 3. Read test ---
    try:
        read_back = await storage.download_file(f"{VAULT_DOCUMENTS}/{test_filename}")
        if read_back != test_content:
            return {
                "ok": False,
                "message": "Read-back content mismatch",
                "details": details,
            }
        details.append("read_test: content matches")
    except Exception as exc:
        logger.error("Read test failed for user %s: %s", user_id[:6] + "***", exc)
        return {"ok": False, "message": f"Read test failed: {exc}", "details": details}

    # --- 4. Delete test ---
    try:
        await storage.delete_file(f"{VAULT_DOCUMENTS}/{test_filename}")
        details.append("delete_test: cleanup succeeded")
    except Exception as exc:
        # Non-fatal: some providers don't support delete, but we log it
        logger.warning("Delete test failed for user %s: %s", user_id[:6] + "***", exc)
        details.append(f"delete_test: skipped ({exc})")

    # --- 5. System file integrity ---
    critical_files = [
        (f"{VAULT_FOLDER}/manifest.json", "vault_manifest"),
        (f"{VAULT_TIMELINE}/{VAULT_TIMELINE_EVENTS_FILENAME}", "timeline_events"),
        (VAULT_OVERLAY_REGISTRY, "overlay_registry"),
    ]
    for file_path, label in critical_files:
        try:
            content = await storage.download_file(file_path)
            data = json.loads(content.decode())
            if data.get("user_id") and data.get("user_id") != user_id:
                return {
                    "ok": False,
                    "message": f"{label} user_id mismatch",
                    "details": details,
                }
            details.append(f"integrity_check: {label} OK")
        except Exception as exc:
            logger.error("Integrity check failed for %s: %s", label, exc)
            return {
                "ok": False,
                "message": f"System file missing or corrupt: {label}",
                "details": details,
            }

    logger.info("Vault system test passed for user %s", user_id[:6] + "***")
    return {"ok": True, "message": "Vault fully operational", "details": details}


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
    1. Create folders (including .auth/)
    2. Place system files (Rehome, README, vault manifest)
    3. Store encrypted token backup (.auth/token.enc + backup)
    4. Read-back verification (prove provider accepted writes)
    5. Mark vault_initialized gate (only after verified)

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

    # 3. Initialize vault data files (timeline events, overlay registry)
    try:
        await _initialize_vault_data_files(provider_name, access_token, user_id)
    except Exception as exc:
        logger.error("Vault data file initialization failed for user %s: %s", user_id[:6] + "***", exc)
        return {"ok": False, "message": f"Data file initialization failed: {exc}"}

    # 4. Encrypted token backup (non-fatal — vault works without it)
    try:
        await _store_encrypted_token_backup(provider_name, access_token, user_id)
    except Exception as exc:
        logger.warning(
            "Encrypted token backup failed for user %s: %s (non-fatal, continuing)",
            user_id[:6] + "***", exc,
        )

    # 5. Comprehensive system test (write + read + delete + integrity)
    test_result = await _verify_system_check(provider_name, access_token, user_id, config)
    if not test_result["ok"]:
        return {"ok": False, "message": test_result["message"]}

    # 6. Mark gate — vault creation IS activation
    await mark_gate(db, user_id, "vault_initialized")

    return {
        "ok": True,
        "message": "Vault created, provisioned, and verified",
        "details": test_result.get("details", []),
    }


async def verify_vault(
    user_id: str,
    provider_name: str,
    access_token: str,
    config: OnboardingConfig,
) -> dict:
    """
    Verify vault is accessible. Called by the vault-setup page after init.
    Runs the full system test if vault has been initialized.
    Returns: {"ok": True/False, "accessible": bool, "details": list}
    """
    try:
        # Quick folder check first
        accessible = await verify_vault_folders(provider_name, access_token, config.vault_folders)
        if not accessible:
            return {"ok": True, "accessible": False, "details": ["folder_access_check: failed"]}

        # Full system test for initialized vaults
        test_result = await _verify_system_check(provider_name, access_token, user_id, config)
        return {
            "ok": test_result["ok"],
            "accessible": test_result["ok"],
            "details": test_result.get("details", []),
        }
    except Exception as exc:
        logger.error("Vault verification failed for user %s: %s", user_id[:6] + "***", exc)
        return {"ok": False, "accessible": False, "error": str(exc)}
