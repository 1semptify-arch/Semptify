"""
External SDK Permissions — Phase 3.2c

Least-privilege permission system for external modules. Each permission
must be declared in the module's semptify.module.json manifest and approved
by an admin before the module can use it.
"""

from collections.abc import Iterable
from enum import StrEnum


class Permission(StrEnum):
    """All permissions available to external modules.

    Forbidden for external modules (never granted):
      - Direct DB access
      - Direct Redis access
      - Access to other modules' internals
      - Access to user PII beyond declared permissions
      - Network calls to non-declared domains
      - File system access outside sandbox
    """

    # Vault
    VAULT_READ = "vault.read"
    VAULT_WRITE = "vault.write"

    # Timeline
    TIMELINE_READ = "timeline.read"
    TIMELINE_WRITE = "timeline.write"

    # Overlay
    OVERLAY_READ = "overlay.read"
    OVERLAY_WRITE = "overlay.write"

    # Documents
    DOCUMENT_READ = "document.read"
    DOCUMENT_WRITE = "document.write"

    # Notifications
    NOTIFICATION_SEND = "notification.send"

    # User profile (limited)
    USER_PROFILE_READ = "user.profile.read"
    USER_CONTACTS_READ = "user.contacts.read"


# All valid permission strings
ALL_PERMISSIONS: frozenset[str] = frozenset(p.value for p in Permission)


class PermissionDeniedError(Exception):
    """Raised when an external module attempts an action it doesn't have permission for."""

    def __init__(self, permission: str, action: str = ""):
        self.permission = permission
        self.action = action
        super().__init__(
            f"Permission denied: external module lacks '{permission}'" + (f" for action '{action}'" if action else "")
        )


class PermissionSet:
    """Immutable set of permissions granted to an external module.

    Use `has()` to check before performing an action. Use `require()` to
    raise PermissionDeniedError if missing.
    """

    def __init__(self, permissions: Iterable[str]):
        validated: set[str] = set()
        for p in permissions:
            if p not in ALL_PERMISSIONS:
                raise ValueError(f"Unknown permission: {p!r}. Valid: {sorted(ALL_PERMISSIONS)}")
            validated.add(p)
        self._permissions: frozenset[str] = frozenset(validated)

    @property
    def permissions(self) -> frozenset[str]:
        return self._permissions

    def has(self, permission: str) -> bool:
        return permission in self._permissions

    def require(self, permission: str, action: str = "") -> None:
        if not self.has(permission):
            raise PermissionDeniedError(permission, action)

    def to_list(self) -> list:
        return sorted(self._permissions)

    def __contains__(self, permission: str) -> bool:
        return self.has(permission)

    def __len__(self) -> int:
        return len(self._permissions)

    def __repr__(self) -> str:
        return f"PermissionSet({self.to_list()})"
