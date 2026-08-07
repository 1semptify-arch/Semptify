"""
Semptify Auth SDK — User ID
============================
User ID encodes provider + role + unique identifier in one string.

Format: <provider_code><role_code><8-char-random>
Example: GU7x9kM2pQ = Google Drive + Tenant + 7x9kM2pQ

Zero framework dependencies. Pure Python.
Wraps app.core.user_id — single source of truth stays in core.
"""

from dataclasses import dataclass

from app.core.user_id import (
    generate_user_id,
    parse_user_id as _parse_user_id,
)


@dataclass(frozen=True)
class UserIdComponents:
    """Parsed components of a Semptify user ID."""
    provider: str | None
    role: str | None
    unique_part: str | None
    raw: str

    @property
    def is_valid(self) -> bool:
        return self.provider is not None and self.role is not None


def make_user_id(provider: str, role: str = "tenant") -> str:
    """
    Generate a new user ID encoding provider and role.

    Args:
        provider: google_drive | dropbox | onedrive
        role: tenant | advocate | legal | manager | admin

    Returns:
        10-char ID like 'GU7x9kM2pQ'
    """
    return generate_user_id(provider, role)


def parse_user_id(user_id: str) -> UserIdComponents:
    """
    Parse a Semptify user ID into its components.

    Args:
        user_id: Raw or HMAC-signed user ID

    Returns:
        UserIdComponents with provider, role, unique_part
    """
    clean = user_id.split(".")[0] if user_id and "." in user_id else user_id
    provider, role, unique = _parse_user_id(clean)
    return UserIdComponents(
        provider=provider,
        role=role,
        unique_part=unique,
        raw=clean,
    )
