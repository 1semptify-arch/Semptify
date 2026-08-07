"""
External Module Context — Phase 3.2a

The context object passed to every external SDK client. It carries:
  - module_name: the external module's name (for audit logging)
  - vendor: the vendor name
  - user_id: the user on whose behalf the module is acting
  - permissions: the PermissionSet granted to this module
  - request_id: optional request correlation ID

External modules receive this context from the external_loader and pass
it to each SDK client call. The context is immutable.
"""
from dataclasses import dataclass

from app.sdk.external.permissions import PermissionSet


@dataclass(frozen=True)
class ExternalModuleContext:
    """Immutable context for an external module invocation."""

    module_name: str
    vendor: str
    user_id: str
    permissions: PermissionSet
    request_id: str | None = None
    jurisdiction: str | None = None

    def require_permission(self, permission: str, action: str = "") -> None:
        """Raise PermissionDeniedError if the module lacks the permission."""
        self.permissions.require(permission, action)

    def to_dict(self) -> dict:
        return {
            "module_name": self.module_name,
            "vendor": self.vendor,
            "user_id": self.user_id,
            "permissions": self.permissions.to_list(),
            "request_id": self.request_id,
            "jurisdiction": self.jurisdiction,
        }
