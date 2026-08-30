"""UI Composer Familiarity Tapering helpers.

Implements the real tapering dial for single-function in-task guide pages:
- Loads the tenant's Experience Token from cloud storage when connected.
- Falls back to a signed `semptify_exp_token` cookie for pre-OAuth / unauth users.
- Records per-function exposure and returns the `intensity_level` and
  `exposure_count` that the `process_indicator` macro uses to choose how
  much narration to show.

New users (no token or empty exposure tallies) start at `intensity_level=High`
per the Progressive Disclosure rule, even though `ExperienceToken` keeps its
existing `Standard` default for other surfaces.
"""

from __future__ import annotations

import base64
import hmac
import json
import logging
from hashlib import sha256

from fastapi import Request
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.cookie_auth import extract_user_id
from app.core.experience_token import (
    ExperienceToken,
    IntensityLevel,
    load_experience_token,
    record_exposure,
    save_experience_token,
)

logger = logging.getLogger(__name__)

EXPERIENCE_TOKEN_COOKIE_NAME = "semptify_exp_token"
_EXPERIENCE_COOKIE_MAX_AGE = 365 * 24 * 60 * 60  # 1 year


def _b64url_encode(value: str) -> str:
    """URL-safe base64 encode without padding."""
    return base64.urlsafe_b64encode(value.encode("utf-8")).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> str:
    """URL-safe base64 decode, tolerant of missing padding."""
    padding = 4 - (len(value) % 4)
    if padding != 4:
        value += "=" * padding
    return base64.urlsafe_b64decode(value.encode("ascii")).decode("utf-8")


def _sign(value: str) -> str:
    """HMAC-SHA256 sign a value, returning `value.signature`."""
    secret = get_settings().secret_key.encode("utf-8")
    sig = hmac.new(secret, value.encode("utf-8"), sha256).hexdigest()
    return f"{value}.{sig}"


def _unsign(signed: str) -> str | None:
    """Verify an HMAC-SHA256 signed value. Returns the payload or None."""
    if "." not in signed:
        return None
    value, provided_sig = signed.rsplit(".", 1)
    secret = get_settings().secret_key.encode("utf-8")
    expected_sig = hmac.new(secret, value.encode("utf-8"), sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, provided_sig):
        return None
    return value


def _token_to_cookie(token: ExperienceToken) -> str:
    """Serialize and sign an Experience Token for a cookie."""
    payload = _b64url_encode(token.model_dump_json())
    return _sign(payload)


def _token_from_cookie(signed: str) -> ExperienceToken | None:
    """Deserialize a signed Experience Token cookie."""
    payload = _unsign(signed)
    if payload is None:
        return None
    try:
        raw = _b64url_decode(payload)
        return ExperienceToken.model_validate_json(raw)
    except (ValidationError, json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("Malformed experience token cookie")
        return None


def _new_token(object_type: str) -> ExperienceToken:
    """Return a fresh token for a new user, defaulting to High intensity."""
    return ExperienceToken(
        exposure_tallies={object_type: 0},
        intensity_level=IntensityLevel.HIGH,
        token_version=1,
    )


def _ensure_high_for_new_user(token: ExperienceToken, object_type: str) -> ExperienceToken:
    """If the token has no exposure history, treat this as a first encounter.

    Returns a token with `intensity_level=High` and an initial zero tally.
    """
    if token.exposure_tallies:
        return token
    return token.model_copy(
        update={
            "exposure_tallies": {object_type: 0},
            "intensity_level": IntensityLevel.HIGH,
        }
    )


async def load_and_record_exposure(
    request: Request,
    object_type: str,
    db: AsyncSession | None = None,
) -> tuple[ExperienceToken, bool]:
    """Load the Experience Token, record one exposure, save where possible.

    Returns `(token, saved_to_cloud)`. When `saved_to_cloud` is False the
    caller should persist the token via `set_experience_token_cookie`.
    """
    user_id = extract_user_id(request) or ""

    token: ExperienceToken | None = None
    saved_to_cloud = False

    if user_id:
        try:
            token = await load_experience_token(user_id, db)
        except Exception:
            logger.exception("Failed to load Experience Token from storage for %s", user_id[:6])

    if token is None:
        signed = request.cookies.get(EXPERIENCE_TOKEN_COOKIE_NAME, "")
        if signed:
            token = _token_from_cookie(signed)

    if token is None:
        token = _new_token(object_type)
    else:
        token = _ensure_high_for_new_user(token, object_type)

    _, token = record_exposure(token, object_type)

    if user_id:
        try:
            saved_to_cloud = await save_experience_token(user_id, token, db)
        except Exception:
            logger.exception("Failed to save Experience Token to storage for %s", user_id[:6])

    return token, saved_to_cloud


def set_experience_token_cookie(response: Response, token: ExperienceToken) -> None:
    """Set the signed Experience Token cookie on a response."""
    if response is None:
        return
    response.set_cookie(
        key=EXPERIENCE_TOKEN_COOKIE_NAME,
        value=_token_to_cookie(token),
        max_age=_EXPERIENCE_COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
        path="/",
    )


async def get_tapering_context(
    request: Request,
    object_type: str,
    db: AsyncSession | None = None,
) -> dict[str, object]:
    """Return the tapering context for a function and request.

    Loads the token, records this exposure, attempts cloud save, and returns
    the values the `process_indicator` macro uses.
    """
    token, saved_to_cloud = await load_and_record_exposure(request, object_type, db)

    exposure_count = token.exposure_tallies.get(object_type, 0)
    intensity = token.intensity_level
    if isinstance(intensity, int):
        intensity = IntensityLevel(intensity).name

    return {
        "intensity_level": intensity,
        "exposure_count": exposure_count,
        "experience_token": token,
        "experience_token_saved_to_cloud": saved_to_cloud,
    }
