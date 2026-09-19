"""
Preamble — The one way in.

Every user enters the application through /preamble. This router makes
exactly one decision: where does this specific user go next?

Decision logic:
  1. No cookie          → new user  → onboarding (role selection)
  2. Invalid cookie     → stale     → clear cookie → onboarding
  3. Valid cookie
       a. Storage connects + vault opens → role home via route_user()
          (the home page decides what to show: normal mode when FINALE
          — document_uploaded — is marked, setup mode when it isn't.
          The completed_groups flags are the durable boundary marks.)
       b. Storage/vault won't open → flag-indicated step: provider
          selection when START is missing, role home for anything else,
          or /storage/reconnect when every flag is already marked

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
    # New users start at role selection — there is no pre-account upload step.
    if not raw_cookie:
        logger.debug("Preamble: no cookie → onboarding role select")
        role_stage = navigation.get_stage("role_select")
        role_path = role_stage.path if role_stage else "/onboarding/select-role.html"
        return ssot_redirect(role_path, context="preamble no cookie")

    # ── Validate cookie signature ─────────────────────────────────────────────
    raw_uid = verify_user_id(raw_cookie)
    if not raw_uid:
        logger.warning("Preamble: invalid cookie signature → onboarding")
        role_stage = navigation.get_stage("role_select")
        dest = role_stage.path if role_stage else "/onboarding/select-role.html"
        response = ssot_redirect(dest, context="preamble invalid cookie")
        response.delete_cookie(COOKIE_USER_ID)
        return response

    # ── Connect storage — vault opens → role home, flags route failure ─────
    # The cookie identifies the user; OAuth tokens grant vault access. If
    # storage connects and the vault opens, the user goes to their role home —
    # the home page itself decides setup mode vs normal mode from the FINALE
    # flag. completed_groups is consulted only to route the failure path —
    # a progress marker, never the primary check.
    session = None
    try:
        from app.core.database import get_session_factory
        from app.modules.storage.router import get_valid_session

        factory = get_session_factory()
        async with factory() as db:
            session = await get_valid_session(db, raw_uid, auto_refresh=True)
    except Exception as exc:
        logger.error("Preamble: session lookup error for user %s: %s", raw_uid[:6] + "***", exc)
        return _db_error_response()

    if session and session.get("access_token"):
        # Storage connects — open the vault. The probe doubles as routing
        # input: the document list it fetches answers documents_present, so
        # route_user never re-queries the same index.
        db_user_id = raw_uid.split(".")[0]
        try:
            from app.services.vault_upload_service import VaultUploadService

            docs = await VaultUploadService().get_user_documents(db_user_id)
            documents_present = len(docs) > 0
        except Exception as exc:
            logger.warning(
                "Preamble: vault open failed for user %s: %s — routing via flags",
                raw_uid[:6] + "***",
                exc,
            )
            documents_present = None

        if documents_present is not None:
            # Vault opens → home. Users whose vault opens but hasn't passed
            # the FINALE test-upload land on their home in setup mode — the
            # home page resumes install/verify there, not back in onboarding.
            from app.core.workflow_engine import route_user

            destination = await route_user(raw_uid, documents_present=documents_present)
            logger.info("Preamble: vault open for user %s → %s", raw_uid[:6] + "***", destination)
            return ssot_redirect(destination, context="preamble vault open")

    # ── Storage didn't connect or vault won't open → onboarding ─────────────
    # Gates are progress markers: they tell us WHERE in onboarding to drop
    # the user. Read them only on this failure path.
    try:
        from app.core.database import get_session_factory
        from app.core.onboarding_state import get_onboarding_state

        factory = get_session_factory()
        async with factory() as db:
            state = await get_onboarding_state(raw_uid, db)

            # Auto-repair: valid session exists but the flag was never marked
            # (users who onboarded before the gate system). Storage provably
            # connected — mark it so routing lands on the right step.
            if not state.storage_connected and session and session.get("access_token"):
                from app.modules.onboarding.gates import mark_gate

                await mark_gate(db, raw_uid, "storage_connected")
                logger.info(
                    "Preamble: auto-repaired storage_connected gate for user %s (valid session found)",
                    raw_uid[:6] + "***",
                )
                state = await get_onboarding_state(raw_uid, db)
    except Exception as exc:
        logger.error("Preamble: DB error for user %s: %s", raw_uid[:6] + "***", exc)
        return _db_error_response()

    # Route to the exact next required step — or reconnect when every gate is
    # already marked but the vault itself won't open (dead grant, revoked
    # access, provider outage). A returning user never re-does role select.
    next_path = state.next_required_path
    if next_path is None:
        reconnect_stage = navigation.get_stage("reconnect")
        next_path = reconnect_stage.path if reconnect_stage else "/storage/reconnect"
        logger.info(
            "Preamble: user %s fully onboarded but vault won't open → reconnect",
            raw_uid[:6] + "***",
        )
    else:
        logger.info(
            "Preamble: user %s incomplete (gate=%s) → %s",
            raw_uid[:6] + "***",
            state.next_required_gate,
            next_path,
        )
    return ssot_redirect(next_path, context="preamble vault unavailable")


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
