"""
External SDK — Phase 3.2a

Public SDK for external (third-party) module developers. Provides
least-privilege access to Semptify systems via clearly-scoped clients.

Available clients:
  - vault_client       — Vault access (read/write per permissions)
  - timeline_client    — Timeline event creation/read
  - overlay_client     — Overlay system access
  - document_client    — Document access (read-only by default)
  - notification_client — Send notifications to users

Forbidden for external modules:
  - Direct DB access
  - Direct Redis access
  - Access to other modules' internals
  - Access to user PII beyond declared permissions
  - Network calls to non-declared domains
  - File system access outside sandbox
"""

__version__ = "0.1.0"

from app.sdk.external.context import ExternalModuleContext
from app.sdk.external.document_client import DocumentClient
from app.sdk.external.notification_client import NotificationClient
from app.sdk.external.overlay_client import OverlayClient
from app.sdk.external.permissions import (
    Permission,
    PermissionDeniedError,
    PermissionSet,
)
from app.sdk.external.timeline_client import TimelineClient
from app.sdk.external.vault_client import VaultClient as ExternalVaultClient

__all__ = [
    "Permission",
    "PermissionSet",
    "PermissionDeniedError",
    "ExternalModuleContext",
    "ExternalVaultClient",
    "TimelineClient",
    "OverlayClient",
    "DocumentClient",
    "NotificationClient",
]
