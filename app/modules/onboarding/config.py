"""
OnboardingConfig — Product-level configuration for the onboarding module.

Each Semptify product provides its own config. The module is generic;
the config makes it specific.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from app.core.vault_paths import (
    SEMPTIFY_ROOT,
    SYSTEM_FOLDER,
    AUTH_FOLDER,
    VAULT_ROOT,
    VAULT_DOCUMENTS,
    VAULT_CERTIFICATES,
    VAULT_TIMELINE,
    VAULT_OVERLAYS,
    VAULT_OVERLAY_DOCUMENTS,
    VAULT_OVERLAY_QUERIES,
    VAULT_OVERLAYS_FORMS,
    VAULT_OVERLAY_REDACTIONS,
    VAULT_FOLDER as VAULT_METADATA_FOLDER,
)

# Canonical vault folders — matches what vault.py router expects.
# These MUST stay in sync with app/core/vault_paths.py.
# .Semptify5.0 is REQUIRED before .Semptify5.0/vault and .Semptify5.0/auth
# because Dropbox create_folder_v2 does NOT auto-create parent folders.
CANONICAL_VAULT_FOLDERS = [
    SEMPTIFY_ROOT,              # "Semptify5.0"
    VAULT_ROOT,                 # "Semptify5.0/Vault"
    VAULT_DOCUMENTS,            # "Semptify5.0/Vault/documents"
    VAULT_CERTIFICATES,         # "Semptify5.0/Vault/certificates"
    VAULT_TIMELINE,             # "Semptify5.0/Vault/timeline"
    VAULT_OVERLAYS,             # "Semptify5.0/Vault/overlays"
    VAULT_OVERLAY_DOCUMENTS,    # "Semptify5.0/Vault/overlays/documents"
    VAULT_OVERLAY_QUERIES,      # "Semptify5.0/Vault/overlays/queries"
    VAULT_OVERLAYS_FORMS,       # "Semptify5.0/Vault/overlays/forms"
    VAULT_OVERLAY_REDACTIONS,   # "Semptify5.0/Vault/overlays/redactions"
    SYSTEM_FOLDER,              # "Semptify5.0/.semptify" (parent must exist before children)
    AUTH_FOLDER,                # "Semptify5.0/.semptify/auth"
    VAULT_METADATA_FOLDER,      # "Semptify5.0/.semptify/vault"
]


@dataclass
class OnboardingConfig:
    """
    Configuration for the onboarding module.

    Attributes:
        product_name:          Human-readable product name (shown in UI).
        allowed_roles:         Roles available during role selection.
        allowed_providers:     Cloud storage providers offered to the user.
        vault_folders:         Folder paths to create in the user's cloud storage.
        on_complete_redirect:  Where to send the user after onboarding finishes.
        gates:                 Serial gates the user must pass. Default: storage + vault.
        oauth_scopes:          Per-provider OAuth scope overrides. Uses defaults if empty.
        route_prefix:          URL prefix for all onboarding routes.
        cookie_name:           Auth cookie name.
        cookie_max_age:        Cookie lifetime in seconds (default 1 year).
        cookie_secure:         HTTPS-only cookies (True in production).
        hmac_signed:           Whether cookies are HMAC-signed.
    """

    # --- Required ---
    product_name: str
    allowed_roles: List[str]
    allowed_providers: List[str]
    on_complete_redirect: str

    # --- Vault folders (defaults to canonical paths from vault_paths.py) ---
    vault_folders: List[str] = field(default_factory=lambda: list(CANONICAL_VAULT_FOLDERS))

    # --- Gates (serial, each unlocks next) ---
    gates: List[str] = field(default_factory=lambda: [
        "storage_connected",
        "vault_initialized",
        "document_uploaded",  # Full pipeline tested: certificate → registry → overlay → event bus
    ])

    # --- OAuth ---
    oauth_scopes: dict = field(default_factory=dict)

    # --- Routing ---
    route_prefix: str = "/onboarding"

    # --- Cookie ---
    cookie_name: str = "semptify_uid"
    cookie_max_age: int = 365 * 24 * 60 * 60
    cookie_secure: bool = True
    hmac_signed: bool = True

    # --- Gate middleware ---
    # Set to False when StorageRequirementMiddleware is already registered for
    # the same app — avoids duplicate gate enforcement that causes redirect loops.
    enable_gate_middleware: bool = True

    # --- Provider defaults (used when oauth_scopes not overridden) ---
    DEFAULT_OAUTH_CONFIGS: dict = field(default_factory=lambda: {
        "google_drive": {
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
            "scopes": [
                "https://www.googleapis.com/auth/drive.file",
                "https://www.googleapis.com/auth/userinfo.email",
            ],
        },
        "dropbox": {
            "auth_url": "https://www.dropbox.com/oauth2/authorize",
            "token_url": "https://api.dropboxapi.com/oauth2/token",
            "userinfo_url": "https://api.dropboxapi.com/2/users/get_current_account",
            "scopes": [],
        },
        "onedrive": {
            "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            "userinfo_url": "https://graph.microsoft.com/v1.0/me",
            "scopes": ["Files.ReadWrite.AppFolder", "User.Read", "offline_access"],
        },
    })

    def get_oauth_config(self, provider: str) -> dict:
        """Get OAuth config for a provider, with scope overrides applied."""
        base = self.DEFAULT_OAUTH_CONFIGS.get(provider, {})
        if provider in self.oauth_scopes:
            base = {**base, "scopes": self.oauth_scopes[provider]}
        return base

    def get_allowed_provider_configs(self) -> dict:
        """Return only the OAuth configs for allowed providers."""
        return {
            p: self.get_oauth_config(p)
            for p in self.allowed_providers
            if p in self.DEFAULT_OAUTH_CONFIGS
        }
