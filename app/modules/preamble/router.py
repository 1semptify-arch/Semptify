"""
Preamble — The one way in.

Every user enters the application through /preamble. This router makes
exactly one decision: where does this specific user go next?

Decision logic:
  1. No cookie          → new user  → onboarding (role select)
  2. Invalid cookie     → stale     → clear cookie → onboarding
  3. Valid cookie
       a. All gates done → returning user → role-specific home
       b. Partial gates  → incomplete     → exact next required step
       c. No gates done  → new account    → start of onboarding

This is the ONLY place in the codebase that branches new vs returning.
Nothing downstream needs to make this decision again.

Expansion: The welcome page content (what Semptify is, mission, etc.)
lives in the static welcome page served at /. Preamble's job is routing,
not content. Add content to the welcome page, not here.
"""
# Migrated from app/routers/preamble.py into the preamble SDK module.
# All imports remain absolute since preamble is a CORE module.

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.cookie_auth import verify_user_id
from app.core.navigation import navigation
from app.core.ssot_guard import ssot_redirect
from app.core.user_id import COOKIE_USER_ID

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Preamble"])


@router.get("/preamble", response_class=HTMLResponse)
async def preamble(request: Request):
    """
    Single entry point — routes every user to exactly where they need to go.

    Called by:
    - The welcome page CTA button
    - Any middleware that needs to restart the flow
    - Root / redirect (unauthenticated users)
    """
    _raw = request.cookies.get(COOKIE_USER_ID)
    raw_cookie = str(_raw) if _raw is not None else None

    # ── Fast path: no cookie = definitely new user ────────────────────────────
    if not raw_cookie:
        logger.debug("Preamble: no cookie → onboarding")
        role_stage = navigation.get_stage("role_select")
        role_path = role_stage.path if role_stage else "/onboarding/select-role.html"
        return ssot_redirect(role_path, context="preamble no cookie")

    # ── Validate cookie signature ─────────────────────────────────────────────
    raw_uid = verify_user_id(raw_cookie)
    if not raw_uid:
        logger.warning("Preamble: invalid cookie signature → onboarding")
        role_stage = navigation.get_stage("role_select")
        role_path = role_stage.path if role_stage else "/onboarding/select-role.html"
        response = ssot_redirect(role_path, context="preamble invalid cookie")
        response.delete_cookie(COOKIE_USER_ID)
        return response

    # ── Read gate state (one DB read) ─────────────────────────────────────────
    try:
        from app.core.database import get_session_factory
        from app.core.onboarding_state import get_onboarding_state

        factory = get_session_factory()
        async with factory() as db:
            state = await get_onboarding_state(raw_uid, db)

            # ── Auto-repair: If user has valid OAuth but missing storage_connected gate ──
            # This handles users who onboarded before the gate system was implemented
            if not state.storage_connected:
                from app.modules.storage.router import get_valid_session

                session = await get_valid_session(db, raw_uid, auto_refresh=False)
                if session and session.get("access_token"):
                    # Valid tokens exist — auto-mark the gate to prevent repeated onboarding
                    from app.modules.onboarding.gates import mark_gate

                    await mark_gate(db, raw_uid, "storage_connected")
                    logger.info(
                        "Preamble: auto-repaired storage_connected gate for user %s (valid tokens found)",
                        raw_uid[:6] + "***",
                    )
                    # Re-read state after auto-repair
                    state = await get_onboarding_state(raw_uid, db)
    except Exception as exc:
        logger.error("Preamble: DB error for user %s: %s", raw_uid[:6] + "***", exc)
        return _db_error_response()

    # ── Route based on gate state ─────────────────────────────────────────────
    if state.is_fully_onboarded:
        # Returning user — send to their role-specific home
        from app.core.workflow_engine import route_user

        destination = await route_user(raw_uid)
        logger.info("Preamble: returning user %s → %s", raw_uid[:6] + "***", destination)
        return ssot_redirect(destination, context="preamble returning user")

    # New or incomplete — send to exact next required step
    next_path = state.next_required_path
    if next_path is None:
        role_stage = navigation.get_stage("role_select")
        next_path = role_stage.path if role_stage else "/onboarding/select-role.html"

    logger.info(
        "Preamble: user %s incomplete (gate=%s) → %s",
        raw_uid[:6] + "***",
        state.next_required_gate,
        next_path,
    )
    return ssot_redirect(next_path, context="preamble incomplete onboarding")


def _db_error_response() -> HTMLResponse:
    """
    Honest error page shown when the DB is unreachable during preamble routing.
    Returns 503 with retry + start-fresh options. Never silently redirects.
    """
    return HTMLResponse(
        content="""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Connection Issue — Semptify</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #fdfcfa; color: #1e293b; min-height: 100vh;
         display: flex; align-items: center; justify-content: center; margin: 0; }
  .card { max-width: 420px; width: 90%; background: white; padding: 2.5rem 2rem;
          border-radius: 16px; box-shadow: 0 4px 32px rgba(0,0,0,0.09); text-align: center; }
  h1 { font-size: 1.4rem; color: #1e3a5f; margin: 0 0 0.75rem; }
  p { color: #64748b; line-height: 1.6; margin: 0 0 1.75rem; }
  .actions { display: flex; gap: 0.75rem; justify-content: center; flex-wrap: wrap; }
  .retry-btn { background: #1e3a5f; color: white; border: none; padding: 0.7rem 1.4rem;
               border-radius: 8px; font-size: 0.95rem; cursor: pointer; }
  .retry-btn:hover { background: #162d4a; }
  .fresh-btn { background: transparent; color: #64748b; border: 1px solid #e2e8f0;
               padding: 0.7rem 1.4rem; border-radius: 8px; font-size: 0.95rem; cursor: pointer; }
  .fresh-btn:hover { border-color: #cbd5e1; color: #475569; }
</style>
</head><body>
<div class="card">
  <h1>Having trouble connecting</h1>
  <p>We're experiencing a temporary issue reaching our servers.<br>
     Your data is safe — this is not a problem with your account.</p>
  <div class="actions">
    <button class="retry-btn" onclick="window.location.reload()">Try Again</button>
    <button class="fresh-btn"
      onclick="document.cookie='semptify_uid=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/';window.location.href='/onboarding/select-role.html'">
      Start Fresh
    </button>
  </div>
</div>
</body></html>""",
        status_code=503,
    )
