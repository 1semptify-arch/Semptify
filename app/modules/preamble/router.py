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
from typing import Optional

from fastapi import APIRouter, Cookie, Request
from fastapi.responses import HTMLResponse

from app.core.navigation import navigation
from app.core.ssot_guard import ssot_redirect
from app.core.cookie_auth import verify_user_id
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
    raw_cookie = request.cookies.get(COOKIE_USER_ID)

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
    except Exception as exc:
        logger.warning("Preamble: DB error for user %s: %s — sending to onboarding", raw_uid[:6] + "***", exc)
        role_stage = navigation.get_stage("role_select")
        role_path = role_stage.path if role_stage else "/onboarding/select-role.html"
        return ssot_redirect(role_path, context="preamble db error")

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
