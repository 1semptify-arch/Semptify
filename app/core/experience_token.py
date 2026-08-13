"""Experience Token — privacy-safe familiarity/preference storage.

Implements ADR-0008 §2.7: a small preferences file stored in the tenant's own
connected cloud storage using the existing storage-as-identity OAuth flow.
Semptify servers never hold this data in a server-side table keyed to tenant
or user ID.

For tenants without connected storage yet (pre-OAuth), the service falls back
to a session-local dict supplied by the caller. That state resets with the
session and does not identify the tenant to Semptify.
"""

from __future__ import annotations

import json
import logging
from enum import IntEnum
from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auto_refresh import ensure_valid_token
from app.core.user_id import get_provider_from_user_id
from app.core.vault_paths import EXPERIENCE_TOKEN_FILE
from app.services.storage import get_provider

logger = logging.getLogger(__name__)

DEFAULT_TOKEN_VERSION = 1


class IntensityLevel(IntEnum):
    """Tenant-controlled explanation/momentum intensity scalar from ADR-0008 §2.8."""

    OFF = 0
    SUBTLE = 1
    STANDARD = 2
    HIGH = 3


DEFAULT_INTENSITY_LEVEL = IntensityLevel.STANDARD


class ExperienceToken(BaseModel):
    """Privacy-safe familiarity and preference state for the Information Orchestrator.

    - `exposure_tallies` maps object_type to the number of times the tenant has
      encountered that type. It is intentionally not keyed to a Semptify user ID.
    - `intensity_level` is a 0-3 scalar controlling warmth/frequency of momentum
      and explanation (Off / Subtle / Standard / High).
    - `token_version` starts at 1 so future schema changes can migrate existing
      tokens in tenant storage.
    """

    exposure_tallies: dict[str, int] = Field(
        default_factory=dict,
        description="Per object_type exposure counts.",
    )
    intensity_level: IntensityLevel = Field(
        default=DEFAULT_INTENSITY_LEVEL,
        description="Multiplier on momentum frequency and explanation warmth.",
    )
    token_version: int = Field(
        default=DEFAULT_TOKEN_VERSION,
        ge=1,
        description="Schema version for forward compatibility.",
    )

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    @field_validator("exposure_tallies")
    @classmethod
    def _non_negative_tallies(cls, value: dict[str, int]) -> dict[str, int]:
        """Ensure all exposure tallies are non-negative."""
        for object_type, count in value.items():
            if count < 0:
                raise ValueError(f"exposure_tally for {object_type} cannot be negative")
        return value


async def load_experience_token(
    user_id: str,
    db: AsyncSession | None = None,
    session_state: dict | None = None,
) -> ExperienceToken:
    """Load the Experience Token for a tenant.

    If the tenant has connected cloud storage, the JSON is read from there.
    Otherwise, fall back to the caller-supplied `session_state` dict. If no
    session state is available, return a fresh default token.
    """
    is_valid, oauth_token, _ = await ensure_valid_token(user_id, db)
    if is_valid and oauth_token and oauth_token.access_token:
        provider_name = get_provider_from_user_id(user_id) or oauth_token.provider
        if provider_name:
            try:
                return await _load_from_storage(provider_name, oauth_token.access_token)
            except Exception as exc:
                logger.warning(
                    "Failed to load Experience Token from storage for %s: %s",
                    user_id[:6],
                    exc,
                )

    # Fallback to session-local state only (pre-OAuth or storage unavailable).
    if session_state is not None and "experience_token" in session_state:
        return ExperienceToken.model_validate(session_state["experience_token"])

    return ExperienceToken()


async def save_experience_token(
    user_id: str,
    token: ExperienceToken,
    db: AsyncSession | None = None,
    session_state: dict | None = None,
) -> bool:
    """Save the Experience Token for a tenant.

    Writes to the tenant's own cloud storage when connected; otherwise writes to
    the caller-supplied `session_state` dict. Returns True if persisted.
    """
    is_valid, oauth_token, _ = await ensure_valid_token(user_id, db)
    if is_valid and oauth_token and oauth_token.access_token:
        provider_name = get_provider_from_user_id(user_id) or oauth_token.provider
        if provider_name:
            try:
                return await _save_to_storage(provider_name, oauth_token.access_token, token)
            except Exception as exc:
                logger.warning(
                    "Failed to save Experience Token to storage for %s: %s",
                    user_id[:6],
                    exc,
                )

    # Fallback to session-local state only.
    if session_state is not None:
        session_state["experience_token"] = token.model_dump(mode="json")
        return True

    return False


def record_exposure(token: ExperienceToken, object_type: str) -> int:
    """Return the new exposure count for an object type and a token with it incremented.

    This is a pure function: the returned `ExperienceToken` is a copy with the
    tally updated. Callers must save it themselves (no side effects on storage).
    """
    tallies = dict(token.exposure_tallies)
    tallies[object_type] = tallies.get(object_type, 0) + 1
    return tallies[object_type], token.model_copy(update={"exposure_tallies": tallies})


async def _load_from_storage(provider_name: str, access_token: str) -> ExperienceToken:
    """Read the Experience Token JSON from the tenant's cloud storage."""
    storage = get_provider(provider_name, access_token=access_token)
    token_path = PurePosixPath(EXPERIENCE_TOKEN_FILE)

    # Ensure the parent folder exists before we try to read.
    folder_created = await storage.create_folder(str(token_path.parent))
    if not folder_created:
        raise RuntimeError(f"Failed to create folder {token_path.parent}")

    try:
        data = await storage.download_file(str(token_path))
    except Exception:
        # Token has not been written yet — return a fresh default.
        return ExperienceToken()

    if not data:
        return ExperienceToken()

    payload = json.loads(data.decode("utf-8"))
    return ExperienceToken.model_validate(payload)


async def _save_to_storage(
    provider_name: str,
    access_token: str,
    token: ExperienceToken,
) -> bool:
    """Write the Experience Token JSON to the tenant's cloud storage."""
    storage = get_provider(provider_name, access_token=access_token)
    token_path = PurePosixPath(EXPERIENCE_TOKEN_FILE)

    # Ensure the parent folder exists. Semptify folders are always created with
    # parents. A False return is an error (Known Failure #1).
    folder_created = await storage.create_folder(str(token_path.parent))
    if not folder_created:
        raise RuntimeError(f"Failed to create folder {token_path.parent}")

    content = token.model_dump_json(indent=2).encode("utf-8")
    result = await storage.upload_file(
        file_content=content,
        destination_path=str(token_path.parent),
        filename=token_path.name,
        mime_type="application/json",
    )
    return bool(result)


__all__ = [
    "DEFAULT_TOKEN_VERSION",
    "IntensityLevel",
    "DEFAULT_INTENSITY_LEVEL",
    "ExperienceToken",
    "load_experience_token",
    "save_experience_token",
]
