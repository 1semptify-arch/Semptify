"""
Register Vault Installer Module

Simple registration - just add the routes to the app.
"""

import logging

from fastapi import FastAPI

from .routes import create_router

logger = logging.getLogger(__name__)


def register_vault_installer(app: FastAPI):
    """
    Register the vault installer module.

    This adds simple vault installation endpoints without complex onboarding.
    """
    router = create_router()
    app.include_router(router)

    logger.info("📦 Vault installer module registered")


# FunctionGroupContracts — simple vault install/activate surface behind
# /api/vault-installer. Not part of the onboarding gate chain.

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="vault_installer",
        group_name="vault_installer_debug",
        title="Vault Installer Debug (SSOT)",
        description="CANONICAL debug info for the vault installer (auth required).",
        inputs=("user_id",),
        outputs=("debug_info",),
        dependencies=("app.modules.vault_installer.routes",),
        deterministic=True,
        tier="T1",
        allowed_routes=("/api/vault-installer/debug",),
        allowed_prefixes=("/api/vault-installer",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="vault_installer",
        group_name="vault_installer_install",
        title="Vault Install (SSOT)",
        description="CANONICAL install and activate the tenant's vault.",
        inputs=("user_id",),
        outputs=("install_result",),
        dependencies=("app.modules.vault_installer.routes",),
        deterministic=False,
        tier="T1",
        allowed_routes=("/api/vault-installer/install",),
        allowed_prefixes=("/api/vault-installer",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="vault_installer",
        group_name="vault_installer_status",
        title="Vault Install Status (SSOT)",
        description="CANONICAL vault installation status for the current user.",
        inputs=("user_id",),
        outputs=("status",),
        dependencies=("app.modules.vault_installer.routes",),
        deterministic=True,
        tier="T1",
        allowed_routes=("/api/vault-installer/status",),
        allowed_prefixes=("/api/vault-installer",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="vault_installer",
        group_name="vault_installer_quick_install",
        title="Vault Quick Install (SSOT)",
        description="CANONICAL one-step vault install using a provider + access token.",
        inputs=("provider", "access_token"),
        outputs=("install_result",),
        dependencies=("app.modules.vault_installer.routes",),
        deterministic=False,
        tier="T1",
        allowed_routes=("/api/vault-installer/quick-install",),
        allowed_prefixes=("/api/vault-installer",),
    )
)
