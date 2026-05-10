"""
Semptify Onboarding Module — Self-contained, reusable onboarding system.

Usage:
    from app.modules.onboarding import register_onboarding, OnboardingConfig

    config = OnboardingConfig(
        product_name="Semptify Tenant Rights",
        allowed_roles=["tenant"],
        allowed_providers=["google_drive", "dropbox", "onedrive"],
        vault_folders=["Semptify5.0/Vault/documents", "Semptify5.0/Vault/evidence"],
        on_complete_redirect="/tenant/home",
    )
    register_onboarding(app, config)
"""

from app.modules.onboarding.config import OnboardingConfig
from app.modules.onboarding.register import register_onboarding

__all__ = ["OnboardingConfig", "register_onboarding"]
