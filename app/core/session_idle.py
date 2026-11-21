"""
G10.8 — Idle session timeout (server-enforced, tamper-proof, restart-safe).

Enforcement target (acceptance matrix, legal_ui_acceptance_matrix.md G10.8):
    Inactivity expiry enforced — baseline ~30 min legal roles / ~60 min tenant —
    with clean re-entry, not a broken half-state.

Why a signed marker cookie instead of the two pre-existing pieces:
- ``advanced_security.SessionManager.inactive_timeout`` is dead config —
  ``validate_session`` updates ``last_activity`` but never compares it against
  the timeout. The class is also process-memory only.
- ``core/sessions.py`` TTL store defaults to ``MemorySessionBackend`` — wiped on
  every Render spin-down/restart. Using it for idle tracking would log every
  user out on each deploy (the exact reconnect-loop failure mode
  RECONNECT-LOOP-001 was filed to fix).

The marker cookie carries ``<user_id>:<unix_ts>.<hmac>``. The HMAC is keyed with
domain ``"idle"`` so a ``semptify_uid`` signature can never be replayed as an
idle signature. The server mints the timestamp — a client cannot forge or
extend it, and the marker survives restarts because it travels with the user.

Sliding window:
- ``set_auth_cookie`` issues the marker together with the auth cookie
  (atomic — a session always starts with a fresh marker).
- ``get_current_user`` verifies the marker on every authenticated request.
  Fresh → request proceeds and flags ``request.state`` for refresh; stale or
  tampered → treated as unauthenticated, which routes through the existing
  clean reconnect flow (``/storage/reconnect``) — no half-state.
- ``IdleActivityMiddleware`` writes the refreshed marker onto the outgoing
  response. A middleware is required because cookies set on a dependency-
  injected ``Response`` never reach the browser when the route returns a
  ``Response`` object directly (FastAPI routing: ``response = raw_response``
  for HTML/redirect responses).

Missing marker → a fresh window is started (graceful migration for 1-year
cookies issued before this feature existed; also covers cookie-less API
clients, whose ``StoredSession`` keeps its own server-side ``expires_at``).
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.key_derivation import hmac_sign, hmac_verify

logger = logging.getLogger(__name__)

IDLE_COOKIE = "semptify_idle"
_IDLE_DOMAIN = "idle"  # HMAC domain separation from the semptify_uid signature
_SEPARATOR = "."

# G10.8 baseline: ~30 min for legal/professional roles, ~60 min for tenants.
IDLE_TIMEOUT_LEGAL_SECONDS = 30 * 60
IDLE_TIMEOUT_TENANT_SECONDS = 60 * 60

# Professional roles handle other people's data — tighter window.
# Anything not listed (tenant, user, donor_supporter, researcher, unknown)
# gets the tenant window.
_LEGAL_SIDE_ROLES = frozenset(
    {"admin", "manager", "advocate", "legal", "judge", "agency", "developer"}
)

# uid second-letter codes that decode to legal-side roles — mirrors the
# role_map in app.core.security.get_current_user (A=admin, M=manager,
# V=advocate, L=legal). U/T letters decode to tenant-side windows.
_LEGAL_ROLE_LETTERS = frozenset({"A", "M", "V", "L"})

# request.state flag consumed by IdleActivityMiddleware.
_STATE_REFRESH_ATTR = "semptify_idle_refresh"

# Re-entry for idle-expired sessions is the provider picker → OAuth handshake.
# /storage/reconnect alone must not resurrect an idle-expired session on
# DB-session validity — that check only proves the browser still holds the
# uid cookie, which is exactly the credential the timeout distrusts.
_RECONNECT_PATH = "/storage/reconnect"
_PROVIDERS_PATH = "/storage/providers"


def idle_timeout_for_role(role: str | None) -> int:
    """Idle window in seconds for a role value (UserRole.value or raw str)."""
    return (
        IDLE_TIMEOUT_LEGAL_SECONDS
        if (role or "") in _LEGAL_SIDE_ROLES
        else IDLE_TIMEOUT_TENANT_SECONDS
    )


def sign_idle_marker(user_id: str, now: int | None = None) -> str:
    """Mint a signed idle marker: ``<user_id>:<unix_ts>.<hmac>``."""
    if not user_id:
        raise ValueError("user_id cannot be empty")
    ts = int(now if now is not None else time.time())
    value = f"{user_id}:{ts}"
    return f"{value}{_SEPARATOR}{hmac_sign(value, domain=_IDLE_DOMAIN)}"


def verify_idle_marker(
    cookie_value: str | None,
    user_id: str,
    timeout_seconds: int,
    now: int | None = None,
) -> str:
    """
    Verify an idle marker for ``user_id`` against ``timeout_seconds``.

    Returns one of:
        "missing" — no marker cookie present (caller may start a fresh window)
        "ok"      — signed, belongs to user_id, within the idle window
        "expired" — signed and belongs to user_id, but the window elapsed
        "invalid" — malformed, tampered, or minted for a different user
    """
    cookie_str = str(cookie_value) if cookie_value is not None else None
    if not cookie_str:
        return "missing"

    parts = cookie_str.rsplit(_SEPARATOR, 1)
    if len(parts) != 2:
        return "invalid"
    value, sig = parts[0], parts[1]

    uid, _, ts_raw = value.rpartition(":")
    if not uid or uid != user_id or not ts_raw.isdigit():
        return "invalid"

    if not hmac_verify(value, sig, domain=_IDLE_DOMAIN):
        return "invalid"

    ts = int(ts_raw)
    current = int(now if now is not None else time.time())
    if ts > current or current - ts > timeout_seconds:
        return "expired"

    return "ok"


def set_idle_cookie(
    response,
    user_id: str,
    max_age: int = 365 * 24 * 60 * 60,
    secure: bool = False,
) -> None:
    """
    Write a fresh idle marker for ``user_id`` (sliding-window reset).

    ``httponly=True`` — only the server reads this cookie. ``max_age`` mirrors
    the auth cookie lifetime; the real timeout is the signed timestamp inside.
    """
    response.set_cookie(
        key=IDLE_COOKIE,
        value=sign_idle_marker(user_id),
        max_age=max_age,
        path="/",
        httponly=True,
        secure=secure,
        samesite="lax",
    )


def clear_idle_cookie(response) -> None:
    """Delete the idle marker (logout/disconnect)."""
    response.delete_cookie(key=IDLE_COOKIE, path="/")


def request_idle_refresh(request, user_id: str) -> None:
    """
    Flag this request for an idle-marker refresh.

    Called by ``get_current_user`` after the marker verifies. Dependency-
    injected Response headers don't reach the browser on routes that return
    a Response object directly, so the refresh is relayed through
    ``request.state`` to ``IdleActivityMiddleware``.
    """
    request.state.semptify_idle_refresh = user_id


def _forced_reauth_redirect(request):
    """
    If the requester holds a valid uid cookie whose idle marker is expired or
    invalid, /storage/reconnect must not silently re-admit them — the OAuth
    provider handshake is the re-entry for idle expiry. Redirect to the
    provider picker; ``set_auth_cookie`` in the OAuth callback re-arms the
    marker once re-verification actually completes.

    Without this, a timed-out user with a still-valid DB session would loop:
    stale marker → denied → reconnect → session valid → home → stale marker →
    denied → …

    Returns a RedirectResponse, or None when the request may pass through:
    no/invalid uid cookie, or a marker that is fresh or absent (absent = the
    graceful pre-feature migration path, not an expired session).
    """
    from app.core.cookie_auth import verify_user_id
    from app.core.user_id import COOKIE_USER_ID

    raw_uid = verify_user_id(request.cookies.get(COOKIE_USER_ID))
    if not raw_uid:
        return None
    # Decode the role the same way get_current_user's uid path does — the
    # second-letter role_map (L/V/A/M → legal-side 30 min), NOT the
    # solo-flattened parse_user_id, which reports every uid as tenant.
    role = "legal" if len(raw_uid) > 1 and raw_uid[1].upper() in _LEGAL_ROLE_LETTERS else "tenant"
    verdict = verify_idle_marker(
        request.cookies.get(IDLE_COOKIE),
        raw_uid,
        idle_timeout_for_role(role),
    )
    if verdict not in ("expired", "invalid"):
        return None
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=_PROVIDERS_PATH, status_code=303)


class IdleActivityMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window refresh + idle-expiry re-entry control.

    Two jobs:
    1. Before the route runs: an idle-expired request aimed at
       /storage/reconnect is redirected to the provider picker so re-entry
       requires the OAuth handshake, not just a live DB session row.
    2. After the route runs: writes the refreshed marker that
       ``get_current_user`` flagged via ``request_idle_refresh``. A middleware
       is required because cookies set on a dependency-injected ``Response``
       never reach the browser when the route returns a ``Response`` object
       directly — this covers dicts, HTMLResponse, RedirectResponse,
       streaming.
    """

    async def dispatch(self, request, call_next):
        if request.url.path.rstrip("/") == _RECONNECT_PATH:
            forced = _forced_reauth_redirect(request)
            if forced is not None:
                return forced
        response = await call_next(request)
        user_id = getattr(request.state, _STATE_REFRESH_ATTR, None)
        if user_id:
            set_idle_cookie(
                response,
                user_id,
                secure=request.url.scheme == "https",
            )
        return response
