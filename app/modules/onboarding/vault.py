"""
Vault setup — uses Vault Installer (SDK-based) to create folder structure,
place system files, and verify write+read access in the user's cloud storage.

This module handles the vault_initialized gate:
1. Call Vault Installer (uses Vault SDK for storage operations)
2. Mark vault_initialized gate (only after verified)

Architecture: Onboarding ▸ Vault Installer ▸ Vault SDK ▸ Storage Providers
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.onboarding.config import OnboardingConfig
from app.modules.onboarding.gates import check_gate
from app.modules.vault_installer import install_vault_for_user

logger = logging.getLogger(__name__)


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
    Full vault initialization using Vault Installer (SDK-based).

    Architecture: Onboarding ▸ Vault Installer ▸ Vault SDK ▸ Storage Providers

    The installer handles:
    1. Create folders (via Vault SDK)
    2. Place system files (README, manifest, vault_status)
    3. Initialize data files (timeline events, overlay registry)
    4. Store encrypted token backup
    5. Comprehensive verification (write/read/delete tests)
    6. Mark vault_initialized gate

    Args:
        base_url: Not used by installer (Rehome handled by vault_manager if needed)

    Returns: {"ok": True/False, "message": str}
    """
    # Check if already done
    already_done = await check_gate(db, user_id, "vault_initialized")
    if already_done:
        return {"ok": True, "message": "Vault already initialized"}

    # Call Vault Installer (handles everything via SDK)
    try:
        result = await install_vault_for_user(
            db=db,
            user_id=user_id,
            provider_name=provider_name,
            access_token=access_token,
        )

        if result.get("success"):
            logger.info("Vault initialized successfully for user %s via installer", user_id[:6] + "***")
            return {
                "ok": True,
                "message": "Vault created, provisioned, and verified via SDK",
                "details": result.get("folders_created", []),
            }
        else:
            logger.error("Vault installation failed for user %s: %s", user_id[:6] + "***", result.get("errors"))
            return {
                "ok": False,
                "message": f"Vault installation failed: {result.get('errors', ['Unknown error'])}",
            }
    except Exception as exc:
        logger.error("Vault initialization failed for user %s: %s", user_id[:6] + "***", exc)
        return {"ok": False, "message": f"Vault initialization failed: {exc}"}


async def verify_vault(
    user_id: str,
    provider_name: str,
    access_token: str,
    config: OnboardingConfig,
) -> dict:
    """
    Verify vault is accessible using Vault SDK.

    Called by the vault-setup page after init.
    Returns: {"ok": True/False, "accessible": bool, "details": list}
    """
    from app.sdk.vault import TENANT_VAULT, VaultClient

    try:
        # Use Vault SDK health check.
        # Only verify TENANT_VAULT folders — those are the only ones created at
        # onboarding. Filedored/overlay/AI folders are on-demand and will not
        # exist yet, so checking them would always report failure.
        vault_client = VaultClient(
            provider=provider_name,
            access_token=access_token,
            user_id=user_id,
            folder_spec=TENANT_VAULT,
        )

        health = await vault_client.health_check()

        return {
            "ok": health.healthy,
            "accessible": health.healthy,
            "details": [
                f"folders_present: {len(health.folders_exist)}",
                f"folders_missing: {len(health.folders_missing)}",
                f"provider_connected: {health.provider_connected}",
            ],
        }
    except Exception as exc:
        logger.error("Vault verification failed for user %s: %s", user_id[:6] + "***", exc)
        return {"ok": False, "accessible": False, "error": str(exc)}
