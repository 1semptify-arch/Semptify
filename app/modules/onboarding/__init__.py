"""
Semptify Onboarding Module — Self-contained, reusable onboarding system.

Usage:
    from app.modules.onboarding import register_onboarding, OnboardingConfig

    config = OnboardingConfig(
        product_name="Semptify Tenant Rights",
        allowed_roles=["tenant"],
        allowed_providers=["google_drive", "dropbox", "onedrive"],
        on_complete_redirect="/tenant/home",
        # vault_folders defaults to CANONICAL_VAULT_FOLDERS from vault_paths.py
    )
    register_onboarding(app, config)
"""

from app.modules.onboarding.config import OnboardingConfig
from app.modules.onboarding.register import register_onboarding

__all__ = ["OnboardingConfig", "register_onboarding"]
