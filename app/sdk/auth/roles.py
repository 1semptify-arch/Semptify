"""
Semptify Auth SDK — Role & Permission Definitions
==================================================
Zero framework dependencies. Pure Python.
"""

from enum import Enum


class UserRole(str, Enum):
    TENANT = "tenant"
    ADVOCATE = "advocate"
    MANAGER = "manager"
    LEGAL = "legal"
    ADMIN = "admin"
    ANONYMOUS = "anonymous"


ROLE_PERMISSIONS: dict[UserRole, frozenset[str]] = {
    UserRole.TENANT: frozenset(
        {
            "read:own_documents",
            "write:own_documents",
            "read:vault",
            "write:vault",
            "read:timeline",
            "write:timeline",
            "read:contacts",
            "write:contacts",
        }
    ),
    UserRole.ADVOCATE: frozenset(
        {
            "read:own_documents",
            "write:own_documents",
            "read:vault",
            "write:vault",
            "read:timeline",
            "write:timeline",
            "read:contacts",
            "write:contacts",
            "read:client_cases",
            "write:client_messages",
            "deliver:documents",
        }
    ),
    UserRole.MANAGER: frozenset(
        {
            "read:own_documents",
            "write:own_documents",
            "read:vault",
            "write:vault",
            "read:timeline",
            "write:timeline",
            "read:contacts",
            "write:contacts",
            "read:client_cases",
            "write:client_messages",
            "manage:cases",
        }
    ),
    UserRole.LEGAL: frozenset(
        {
            "read:own_documents",
            "write:own_documents",
            "read:vault",
            "write:vault",
            "read:timeline",
            "write:timeline",
            "read:contacts",
            "write:contacts",
            "read:client_cases",
            "write:legal_filings",
            "read:court_forms",
            "write:court_forms",
            "access:privilege_docs",
        }
    ),
    UserRole.ADMIN: frozenset(
        {
            "read:all",
            "write:all",
            "admin:users",
            "admin:system",
            "admin:analytics",
        }
    ),
    UserRole.ANONYMOUS: frozenset(
        {
            "read:public",
        }
    ),
}


def get_permissions(role: UserRole) -> frozenset[str]:
    """Return the permission set for a role."""
    return ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(role: UserRole, permission: str) -> bool:
    """Check if a role has a specific permission."""
    perms = get_permissions(role)
    return permission in perms or "read:all" in perms or "write:all" in perms
