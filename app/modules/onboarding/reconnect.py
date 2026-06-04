"""
Reconnect — returning user re-authorization flow.

Ownership: This lives in the onboarding module because reconnect is a gate
enforcement concern. When the storage_connected gate lapses (token expired),
this flow restores it. The onboarding module owns the full lifecycle of the
storage_connected gate — both setting it (new user) and restoring it (token expiry).

Mounted at /storage/reconnect (SSOT-registered path) so no other code changes.

Flow:
  1. Cookie + valid session       → route to role home or return_to
  2. Cookie + expired + provider  → silent OAuth (user never sees this page)
  3. Cookie + unknown provider    → show provider picker with auto-reconnect
  4. No cookie                    → show provider picker (lost state)
"""

import json as _json
import logging
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.cookie_auth import verify_user_id
from app.core.database import get_db
from app.core.navigation import navigation
from app.core.ssot_guard import ssot_redirect
from app.core.user_id import parse_user_id, get_provider_from_user_id
from app.core.workflow_engine import route_user as _route_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["onboarding", "reconnect"])

OAUTH_CONFIGS = {
    "google_drive": {},
    "dropbox": {},
    "onedrive": {},
}


@router.get("/storage/reconnect", response_class=HTMLResponse)
async def reconnect_storage(
    request: Request,
    semptify_uid: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
    return_to: Optional[str] = Query(None),
):
    """
    Reconnect page for returning users whose storage token has expired.

    Mounted at /storage/reconnect to match the SSOT-registered path.
    Owned by the onboarding module — reconnect is a gate enforcement concern,
    not a storage infrastructure concern.
    """
    from app.modules.storage.router import get_valid_session

    raw_uid = verify_user_id(semptify_uid) if semptify_uid else None

    safe_return_to = None
    if return_to and return_to.startswith("/") and not return_to.startswith("//"):
        safe_return_to = return_to

    if raw_uid:
        provider, _, _ = parse_user_id(raw_uid)

        session = await get_valid_session(db, raw_uid, auto_refresh=True)
        if session:
            landing = safe_return_to if safe_return_to else await _route_user(raw_uid)
            logger.info("Reconnect: session valid, routing to %s for user=%s", landing, raw_uid[:4] + "***")
            return ssot_redirect(landing, context="reconnect session valid")

        if provider and provider in OAUTH_CONFIGS:
            logger.info("Reconnect: silent re-auth for user=%s provider=%s return_to=%s",
                        raw_uid[:4] + "***", provider, safe_return_to)
            auth_url = f"/storage/auth/{provider}?existing_uid={raw_uid}"
            if safe_return_to:
                auth_url += f"&return_to={safe_return_to}"
            return ssot_redirect(auth_url, context="reconnect silent reauth")

    return HTMLResponse(content=_reconnect_html(existing_uid=raw_uid, return_to=safe_return_to))


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def _reconnect_html(existing_uid: Optional[str] = None, return_to: Optional[str] = None) -> str:
    """Generate the reconnect page HTML."""
    settings = get_settings()

    known_provider = get_provider_from_user_id(existing_uid) if existing_uid else None

    PROVIDER_CONFIG = {
        "google_drive": ("📁", "Google Drive", settings.google_drive_client_id),
        "dropbox":      ("☁️", "Dropbox",       settings.dropbox_app_key),
        "onedrive":     ("🔵", "OneDrive",      settings.onedrive_client_id),
    }

    if known_provider and known_provider in PROVIDER_CONFIG:
        icon, name, enabled = PROVIDER_CONFIG[known_provider]
        if enabled:
            auto_redirect = f'''
            <div id="reconnecting-msg" style="text-align:center;padding:2rem;">
                <div style="font-size:3rem;margin-bottom:1rem;">🔄</div>
                <h3>Reconnecting to {name}...</h3>
                <p>Your documents are safe. Redirecting you now.</p>
            </div>
            <script>
                setTimeout(function() {{ reconnect('{known_provider}'); }}, 1500);
            </script>
            '''
            other_buttons = "".join(
                f'<button class="btn btn-secondary" onclick="reconnect(\'{pid}\')">'
                f'<span class="btn-icon">{picon}</span><div><small>Use {pname} instead</small></div></button>'
                for pid, (picon, pname, penabled) in PROVIDER_CONFIG.items()
                if pid != known_provider and penabled
            )
            providers_html = auto_redirect + '<div style="margin-top:1rem;opacity:0.8;">' + other_buttons + '</div>'
        else:
            providers_html = _all_provider_buttons(PROVIDER_CONFIG)
    else:
        providers_html = _all_provider_buttons(PROVIDER_CONFIG)

    existing_uid_js = _json.dumps(existing_uid)
    return_to_js = _json.dumps(return_to)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reconnect - Semptify</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #f1f5f9;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .container {{ max-width: 500px; width: 90%; padding: 2rem; }}
        .icon {{ font-size: 4rem; text-align: center; margin-bottom: 1rem; }}
        h1 {{ text-align: center; margin-bottom: 0.5rem; font-size: 1.75rem; }}
        .subtitle {{ text-align: center; color: #94a3b8; margin-bottom: 2rem; }}
        .info-box {{
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid #10b981;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1.5rem;
            font-size: 0.9rem;
        }}
        .button-grid {{ display: grid; gap: 0.75rem; }}
        .btn {{
            display: flex; align-items: center; gap: 1rem;
            padding: 1rem 1.25rem;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px; color: #f1f5f9;
            cursor: pointer; transition: all 0.2s;
            text-align: left; width: 100%;
        }}
        .btn:hover {{ background: rgba(255,255,255,0.15); border-color: rgba(255,255,255,0.3); }}
        .btn-icon {{ font-size: 1.5rem; }}
        .btn-label {{ font-weight: 600; margin-bottom: 0.25rem; }}
        .btn-desc {{ font-size: 0.875rem; opacity: 0.7; }}
        .back-link {{
            display: block; text-align: center; margin-top: 1.5rem;
            color: #64748b; text-decoration: none;
        }}
        .back-link:hover {{ color: #94a3b8; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">👋</div>
        <h1>Welcome Back!</h1>
        <p class="subtitle">Reconnect your storage to restore your documents</p>
        <div class="info-box">
            <strong>No data is lost.</strong> Your documents are safely stored in your cloud account.
            Just reconnect with the same provider you used before.
        </div>
        <div class="button-grid">
            {providers_html}
        </div>
        <a href="/" class="back-link">← Back to welcome page</a>
    </div>
    <script>
        var EXISTING_UID = {existing_uid_js};
        var RETURN_TO = {return_to_js};
        function reconnect(provider) {{
            var url = '/storage/auth/' + provider;
            var params = [];
            if (EXISTING_UID) params.push('existing_uid=' + encodeURIComponent(EXISTING_UID));
            if (RETURN_TO)    params.push('return_to='    + encodeURIComponent(RETURN_TO));
            if (params.length > 0) url += '?' + params.join('&');
            window.location.href = url;
        }}
    </script>
</body>
</html>'''


def _all_provider_buttons(provider_config: dict) -> str:
    """Render buttons for all enabled providers."""
    buttons = "".join(
        f'<button class="btn" onclick="reconnect(\'{pid}\')">'
        f'<span class="btn-icon">{picon}</span>'
        f'<div><div class="btn-label">{pname}</div>'
        f'<div class="btn-desc">Connect with {pname}</div></div></button>'
        for pid, (picon, pname, penabled) in provider_config.items()
        if penabled
    )
    return buttons or '<p style="text-align:center;color:#94a3b8;">No storage providers configured.</p>'
