"""
Onboarding Router — all page and API routes for the onboarding flow.

Routes:
  GET  {prefix}/                     → entry point (role selection)
  GET  {prefix}/providers            → storage provider selection
  GET  {prefix}/auth/{provider}      → initiate OAuth (onboarding-specific)
  GET  {prefix}/callback/{provider}  → OAuth callback (onboarding-specific)
  GET  {prefix}/vault-setup          → vault setup page
  POST {prefix}/api/vault/init       → create vault folders
  GET  {prefix}/api/vault/verify     → verify vault folders
  GET  {prefix}/api/vault/status     → check user auth status
  GET  {prefix}/complete             → route to product home
  GET  {prefix}/status               → gate status check page
"""

import logging
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.cookie_auth import verify_user_id, set_auth_cookie
from app.core.security import require_user, StorageUser
from app.core.workflow_engine import route_user
from app.core.navigation import navigation
from app.core.ssot_guard import ssot_redirect

from app.modules.onboarding.config import OnboardingConfig
from app.modules.onboarding import gates as gate_ops
from app.modules.onboarding import oauth as oauth_ops
from app.modules.onboarding import vault as vault_ops

logger = logging.getLogger(__name__)


def create_router(config: OnboardingConfig) -> APIRouter:
    """
    Factory function — creates an APIRouter wired to the given config.
    Called by register_onboarding().
    """
    router = APIRouter(prefix=config.route_prefix, tags=["onboarding"])

    # ------------------------------------------------------------------
    # Page: Role Selection (entry point)
    # ------------------------------------------------------------------
    @router.get("/", response_class=HTMLResponse)
    async def onboarding_root():
        """Redirect to role selection."""
        role_stage = navigation.get_stage("role_select")
        return ssot_redirect(role_stage.path, context="onboarding_root")

    @router.get("/select-role.html", response_class=HTMLResponse)
    async def role_selection_page():
        """Show role selection page (Jinja2 template)."""
        return HTMLResponse(content=_render_role_selection_page(config))

    @router.get("/start")
    async def onboarding_start(
        semptify_uid: Optional[str] = Cookie(None),
    ):
        """Smart entry: returning user → reconnect, new user → role select."""
        if semptify_uid:
            raw_uid = verify_user_id(semptify_uid)
            if raw_uid:
                return ssot_redirect(navigation.get_reconnect_flow(), context="onboarding_start reconnect")
        role_stage = navigation.get_stage("role_select")
        return ssot_redirect(role_stage.path, context="onboarding_start new_user")

    # ------------------------------------------------------------------
    # Page: Provider Selection
    # ------------------------------------------------------------------
    @router.get("/providers", response_class=HTMLResponse)
    async def providers_page(role: Optional[str] = Query("tenant")):
        """Show storage provider selection. Config-driven provider list."""
        return HTMLResponse(content=_render_providers_page(config))

    # ------------------------------------------------------------------
    # OAuth: Initiate (onboarding-specific callback URL)
    # ------------------------------------------------------------------
    @router.get("/auth/{provider}")
    async def onboarding_oauth_start(
        provider: str,
        role: str = Query("tenant"),
        db: AsyncSession = Depends(get_db),
        request: Request = None,
    ):
        """Initiate OAuth for onboarding. Uses onboarding callback URL."""
        if provider not in config.allowed_providers:
            raise HTTPException(status_code=400, detail=f"Provider '{provider}' not supported")
        allowed_roles = getattr(gate_ops, 'ALLOWED_ROLES', {"tenant"})
        if role not in allowed_roles:
            role = "tenant"

        # Build callback URL — resolve the real public URL (Render proxy-aware)
        from app.core.config import get_settings as _get_settings
        _settings = _get_settings()
        if _settings.public_base_url:
            base_url = _settings.public_base_url.rstrip("/")
        else:
            # Render sets X-Forwarded-Host + X-Forwarded-Proto on every request
            fwd_host = request.headers.get("x-forwarded-host")
            fwd_proto = request.headers.get("x-forwarded-proto", "https")
            if fwd_host:
                base_url = f"{fwd_proto}://{fwd_host}"
            else:
                base_url = str(request.base_url).rstrip("/")
        callback_url = f"{base_url}{config.route_prefix}/callback/{provider}"

        try:
            state = await oauth_ops.create_oauth_state(db, provider, role, callback_url)
            auth_url = oauth_ops.build_oauth_url(config, provider, state, callback_url)
        except Exception as exc:
            logger.exception("OAuth initiation failed: provider=%s role=%s error=%s", provider, role, exc)
            raise HTTPException(status_code=500, detail="OAuth initiation failed") from exc

        logger.info("Onboarding OAuth initiated: provider=%s role=%s callback=%s headers_host=%s headers_proto=%s",
                    provider, role, callback_url,
                    request.headers.get("x-forwarded-host", "NONE"),
                    request.headers.get("x-forwarded-proto", "NONE"))
        # OAuth is external - use direct redirect
        return RedirectResponse(url=auth_url, status_code=302)

    # ------------------------------------------------------------------
    # OAuth: Callback (onboarding-specific)
    # ------------------------------------------------------------------
    @router.get("/callback/{provider}")
    async def onboarding_oauth_callback(
        provider: str,
        code: str = Query(...),
        state: str = Query(...),
        request: Request = None,
        db: AsyncSession = Depends(get_db),
    ):
        """
        Handle OAuth callback for onboarding. This callback:
        1. Exchanges code for tokens
        2. Creates or finds user
        3. Saves session + caches token
        4. Marks storage_connected gate
        5. ALWAYS routes to vault-setup (onboarding callback = vault needed)
        """
        try:
            logger.info("OAuth callback started: provider=%s state=%s", provider, state[:8] + "***")
            
            from app.core.config import get_settings as _get_settings
            _settings = _get_settings()
            if _settings.public_base_url:
                base_url = _settings.public_base_url.rstrip("/")
            else:
                fwd_host = request.headers.get("x-forwarded-host")
                fwd_proto = request.headers.get("x-forwarded-proto", "https")
                if fwd_host:
                    base_url = f"{fwd_proto}://{fwd_host}"
                else:
                    base_url = str(request.base_url).rstrip("/")
            callback_url = f"{base_url}{config.route_prefix}/callback/{provider}"
            
            logger.info("OAuth callback: built callback_url=%s", callback_url)

            result = await oauth_ops.handle_onboarding_callback(
                db=db,
                provider=provider,
                code=code,
                state=state,
                callback_url=callback_url,
                config=config,
            )
            
            logger.info("OAuth callback: handle_onboarding_callback completed")

            user_id = result["user_id"]
            vault_initialized = result["vault_initialized"]
            
            logger.info("OAuth callback: user_id=%s vault_initialized=%s", user_id[:6] + "***", vault_initialized)

            # Determine landing — always route to selected role's home page
            if vault_initialized:
                landing = route_user(user_id)
            else:
                landing = f"{config.route_prefix}/vault-setup"

            logger.info(
                "Onboarding callback complete: user=%s vault=%s → %s",
                user_id[:6] + "***", vault_initialized, landing,
            )

            # Use SSOT-compliant redirect
            from app.core.ssot_guard import ssot_redirect
            response = ssot_redirect(landing, context="onboarding_oauth_callback")
            
            logger.info("OAuth callback: about to set cookie for user=%s", user_id[:6] + "***")
            set_auth_cookie(response, user_id, secure=config.cookie_secure)
            logger.info("OAuth callback: cookie set successfully")
            
            return response
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error("OAuth callback failed: %s\n%s", str(e), tb)
            return HTMLResponse(
                content=f"""<pre style="font-family:monospace;padding:2rem;background:#1e1e1e;color:#f44;max-width:100%;overflow:auto">
<b>OAuth Callback Error (debug mode)</b>

{str(e)}

{tb}
</pre>""",
                status_code=500,
            )

    # ------------------------------------------------------------------
    # Page: Vault Setup
    # ------------------------------------------------------------------
    @router.get("/vault-setup", response_class=HTMLResponse)
    async def vault_setup_page(semptify_uid: Optional[str] = Cookie(None)):
        """Post-OAuth vault initialization page. JS calls /api/vault/init + /verify."""
        if not semptify_uid:
            role_stage = navigation.get_stage("role_select")
            return ssot_redirect(role_stage.path, context="vault_setup no cookie")
        return HTMLResponse(content=_render_vault_setup_page(config))

    # ------------------------------------------------------------------
    # API: Vault Status (auto-installed during OAuth)
    # ------------------------------------------------------------------
    @router.get("/api/vault/status")
    async def vault_status(
        user: StorageUser = Depends(require_user),
        db: AsyncSession = Depends(get_db),
    ):
        """Check vault installation status - auto-installed during OAuth."""
        from app.modules.onboarding.gates import check_gate
        
        vault_initialized = await check_gate(db, user.user_id, "vault_initialized")
        
        return {
            "vault_installed": vault_initialized,
            "storage_connected": True,
            "provider": user.provider.value if hasattr(user.provider, 'value') else str(user.provider),
            "message": "Vault auto-installed during OAuth" if vault_initialized else "Vault installation pending",
            "next_action": "use_vault" if vault_initialized else "oauth_callback_pending",
        }

    # ------------------------------------------------------------------
    # Page: Complete
    # ------------------------------------------------------------------
    @router.get("/complete")
    async def onboarding_complete(semptify_uid: Optional[str] = Cookie(None)):
        """Route to product home page after onboarding."""
        if not semptify_uid:
            role_stage = navigation.get_stage("role_select")
            return ssot_redirect(role_stage.path, context="onboarding_complete no cookie")
        raw_uid = verify_user_id(semptify_uid)
        if not raw_uid:
            role_stage = navigation.get_stage("role_select")
            return ssot_redirect(role_stage.path, context="onboarding_complete bad cookie")
        destination = route_user(raw_uid)
        return ssot_redirect(destination, context="onboarding_complete route_user")

    # ------------------------------------------------------------------
    # Page: Gate Status
    # ------------------------------------------------------------------
    @router.get("/status", response_class=HTMLResponse)
    async def onboarding_status(
        semptify_uid: Optional[str] = Cookie(None),
        db: AsyncSession = Depends(get_db),
    ):
        """Check current gate status and show appropriate page."""
        if not semptify_uid:
            return ssot_redirect(f"{config.route_prefix}/", context="status no cookie")

        raw_uid = verify_user_id(semptify_uid)
        if not raw_uid:
            return ssot_redirect(f"{config.route_prefix}/", context="status bad cookie")

        incomplete = await gate_ops.get_first_incomplete_gate(db, raw_uid, config.gates)
        if incomplete is None:
            return ssot_redirect(config.on_complete_redirect, context="status all gates done")

        return HTMLResponse(content=_render_status_page(config, incomplete))

    # ------------------------------------------------------------------
    # SSOT Navigation API
    # ------------------------------------------------------------------
    @router.get("/ssot-navigation")
    async def ssot_navigation():
        """Export navigation state for static files."""
        return navigation.to_dict()

    return router


# ============================================================================
# Page Renderers (minimal — these generate the HTML that JS drives)
# ============================================================================

def _render_role_selection_page(config: OnboardingConfig) -> str:
    """Render role selection page — all 5 roles, non-tenant marked Coming Soon."""
    providers_path = f"{config.route_prefix}/providers"

    roles = [
        ("tenant",  "🏠", "Tenant",             "I'm renting a home and need to protect my rights", True),
        ("manager", "�", "Worker / Manager",    "I work with multiple clients across housing cases", False),
        ("advocate","⚖️", "Housing Advocate",    "I help tenants navigate housing law", False),
        ("legal",   "📋", "Legal Professional",  "I'm an attorney or paralegal working housing cases", False),
        ("admin",   "🛡️", "Administrator",       "Platform administration and oversight", False),
    ]

    role_cards = ""
    for role_id, icon, name, desc, active in roles:
        if active:
            dest = f"{providers_path}?role={role_id}"
            role_cards += f"""
<a class="role-option active" href="{dest}">
  <div class="role-icon">{icon}</div>
  <div class="role-info">
    <div class="role-name">{name}</div>
    <div class="role-desc">{desc}</div>
  </div>
</a>"""
        else:
            role_cards += f"""
<div class="role-option coming-soon" title="Coming soon">
  <div class="role-icon">{icon}</div>
  <div class="role-info">
    <div class="role-name">{name} <span class="badge">Coming Soon</span></div>
    <div class="role-desc">{desc}</div>
  </div>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Select Your Role — {config.product_name}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #fdfcfa; color: #1e293b; min-height: 100vh; }}
.header {{ background: linear-gradient(135deg, #1e3a5f, #2d5a87); color: white; padding: 2.5rem 2rem; text-align: center; }}
.header h1 {{ font-size: 2rem; font-weight: 400; letter-spacing: -0.02em; }}
.header .sub {{ font-size: 0.95rem; opacity: 0.8; margin-top: 0.4rem; font-style: italic; }}
.container {{ max-width: 560px; margin: 2rem auto; padding: 0 1.5rem 3rem; }}
.role-option {{ border: 2px solid #e2e8f0; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1rem; background: white; display: flex; align-items: center; gap: 1rem; transition: all 0.2s; }}
.role-option.active {{ cursor: pointer; text-decoration: none; color: inherit; }}
.role-option.active:hover {{ border-color: #3b82f6; box-shadow: 0 4px 12px rgba(59,130,246,0.15); transform: translateY(-2px); }}
.role-option.coming-soon {{ opacity: 0.55; cursor: not-allowed; background: #f8fafc; }}
.role-icon {{ font-size: 2rem; flex-shrink: 0; width: 2.5rem; text-align: center; }}
.role-name {{ font-size: 1.05rem; font-weight: 600; color: #1e3a5f; margin-bottom: 0.2rem; display: flex; align-items: center; gap: 0.5rem; }}
.role-desc {{ font-size: 0.875rem; color: #64748b; line-height: 1.4; }}
.badge {{ font-size: 0.65rem; font-weight: 600; background: #f1f5f9; color: #94a3b8; border: 1px solid #e2e8f0; padding: 0.15rem 0.5rem; border-radius: 99px; letter-spacing: 0.04em; text-transform: uppercase; }}
</style>
</head><body>
<div class="header">
  <h1>Who are you?</h1>
  <div class="sub">Select your role to get started with {config.product_name}</div>
</div>
<div class="container">
{role_cards}
</div>
<script src="/js/unified-footer-loader.js"></script>
</body></html>"""

def _render_providers_page(config: OnboardingConfig) -> str:
    """Render storage provider selection page."""
    provider_cards = ""
    provider_info = {
        "google_drive": ("Google Drive", "🟢", "Free 15 GB • Fast sync"),
        "dropbox": ("Dropbox", "🔵", "Free 2 GB • Reliable sync"),
        "onedrive": ("OneDrive", "🟠", "Free 5 GB • Microsoft integration"),
    }
    for p in config.allowed_providers:
        name, icon, desc = provider_info.get(p, (p, "📁", "Cloud storage"))
        provider_cards += f"""
        <button class="provider-card" onclick="selectProvider('{p}')">
            <span class="provider-icon">{icon}</span>
            <span class="provider-name">{name}</span>
            <span class="provider-desc">{desc}</span>
        </button>"""

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Connect Storage — {config.product_name}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: Georgia, serif; background: #fdfcfa; color: #1e293b; min-height: 100vh; }}
.header {{ background: linear-gradient(135deg, #1e3a5f, #2d5a87); color: white; padding: 2.5rem 2rem; text-align: center; }}
.header h1 {{ font-size: 1.8rem; font-weight: 400; }}
.header .sub {{ font-size: 0.95rem; opacity: 0.85; font-style: italic; margin-top: 0.25rem; }}
.container {{ max-width: 600px; margin: 2rem auto; padding: 0 1.5rem; }}
.provider-grid {{ display: grid; gap: 1rem; }}
.provider-card {{ border: 2px solid #e2e8f0; border-radius: 12px; padding: 1.25rem; background: white; cursor: pointer; transition: all 0.2s; text-align: left; display: grid; grid-template-columns: auto 1fr; grid-template-rows: auto auto; gap: 0.25rem 0.75rem; font-family: inherit; }}
.provider-card:hover {{ border-color: #3b82f6; box-shadow: 0 4px 12px rgba(59,130,246,0.12); transform: translateY(-2px); }}
.provider-icon {{ font-size: 1.75rem; grid-row: 1/3; align-self: center; }}
.provider-name {{ font-size: 1.05rem; font-weight: 600; color: #1e3a5f; }}
.provider-desc {{ font-size: 0.85rem; color: #64748b; }}
.trust {{ margin-top: 2rem; padding: 1.25rem; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; font-size: 0.9rem; color: #166534; }}
</style></head><body>
<div class="header">
    <h1>Connect Your Storage</h1>
    <div class="sub">Your documents stay in YOUR cloud — we never store them on our servers</div>
</div>
<div class="container">
    <div class="provider-grid">{provider_cards}</div>
    <div class="trust">
        <strong>Your privacy is protected.</strong> {config.product_name} stores documents in your personal
        cloud storage. We never have access to your files. You can disconnect at any time.
    </div>
</div>
<script>
function selectProvider(provider) {{
    const role = new URLSearchParams(window.location.search).get('role') || 'tenant';
    window.location.href = '{config.route_prefix}/auth/' + provider + '?role=' + role;
}}
</script>
<script src="/js/unified-footer-loader.js"></script>
</body></html>"""


def _render_vault_setup_page(config: OnboardingConfig) -> str:
    """Render vault setup page with JS that calls init + verify APIs."""
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Setting Up Your Vault — {config.product_name}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: Georgia, serif; background: #fdfcfa; color: #1e293b; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; }}
.setup-card {{ max-width: 500px; width: 90%; background: white; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); padding: 2.5rem; text-align: center; }}
h1 {{ font-size: 1.5rem; font-weight: 400; color: #1e3a5f; margin-bottom: 1.5rem; }}
.step {{ display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 0; border-bottom: 1px solid #f1f5f9; text-align: left; }}
.step:last-child {{ border: none; }}
.step-icon {{ width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; flex-shrink: 0; background: #f1f5f9; color: #94a3b8; }}
.step-icon.running {{ background: #dbeafe; color: #3b82f6; animation: pulse 1.5s infinite; }}
.step-icon.done {{ background: #dcfce7; color: #16a34a; }}
.step-icon.error {{ background: #fef2f2; color: #dc2626; }}
.step-label {{ font-size: 0.95rem; }}
.error-msg {{ color: #dc2626; font-size: 0.85rem; margin-top: 1rem; padding: 0.75rem; background: #fef2f2; border-radius: 8px; display: none; }}
@keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}
</style></head><body>
<div class="setup-card">
    <h1>Setting Up Your Secure Vault</h1>
    <div class="step" id="step-auth">
        <div class="step-icon" id="icon-auth">1</div>
        <div class="step-label">Verifying your account</div>
    </div>
    <div class="step" id="step-folders">
        <div class="step-icon" id="icon-folders">2</div>
        <div class="step-label">Creating vault folders</div>
    </div>
    <div class="step" id="step-verify">
        <div class="step-icon" id="icon-verify">3</div>
        <div class="step-label">Verifying vault access</div>
    </div>
    <div class="step" id="step-done">
        <div class="step-icon" id="icon-done">4</div>
        <div class="step-label">Ready to go</div>
    </div>
    <div class="error-msg" id="error-msg"></div>
</div>
<script>
const PREFIX = '{config.route_prefix}';
const COMPLETE_URL = '{config.route_prefix}/complete';

function setStep(id, state) {{
    const icon = document.getElementById('icon-' + id);
    icon.className = 'step-icon ' + state;
    if (state === 'done') icon.textContent = '✓';
    else if (state === 'error') icon.textContent = '✗';
    else if (state === 'running') icon.textContent = '⟳';
}}

function showError(msg) {{
    const el = document.getElementById('error-msg');
    el.textContent = msg;
    el.style.display = 'block';
}}

async function setup() {{
    try {{
        // Step 1: Verify auth
        setStep('auth', 'running');
        const statusResp = await fetch(PREFIX + '/api/vault/status');
        if (!statusResp.ok) {{ throw new Error('Authentication failed — please reconnect storage'); }}
        setStep('auth', 'done');

        // Step 2: Create folders
        setStep('folders', 'running');
        const initResp = await fetch(PREFIX + '/api/vault/init', {{ method: 'POST' }});
        if (!initResp.ok) {{
            const data = await initResp.json().catch(() => ({{}}));
            throw new Error(data.detail || data.message || 'Failed to create vault folders');
        }}
        setStep('folders', 'done');

        // Step 3: Verify
        setStep('verify', 'running');
        const verifyResp = await fetch(PREFIX + '/api/vault/verify');
        if (!verifyResp.ok) {{ throw new Error('Vault verification failed'); }}
        const verifyData = await verifyResp.json();
        if (!verifyData.accessible || !verifyData.ok) {{
            throw new Error(verifyData.error || 'Vault folders not accessible');
        }}
        setStep('verify', 'done');

        // Step 4: Done
        setStep('done', 'done');
        setTimeout(() => {{ window.location.href = COMPLETE_URL; }}, 800);

    }} catch(e) {{
        showError(e.message);
        // Mark current running step as error
        ['auth','folders','verify','done'].forEach(id => {{
            const icon = document.getElementById('icon-' + id);
            if (icon.className.includes('running')) setStep(id, 'error');
        }});
    }}
}}

setup();
</script>
<script src="/js/unified-footer-loader.js"></script>
</body></html>"""


def _render_status_page(config: OnboardingConfig, incomplete_gate: str) -> str:
    """Render a page showing which gate the user needs to complete next."""
    gate_actions = {
        "storage_connected": (
            "Connect Your Storage",
            "You need to connect a cloud storage provider to continue.",
            f"{config.route_prefix}/providers",
        ),
        "vault_initialized": (
            "Set Up Your Vault",
            "Your storage is connected but vault folders haven't been created yet.",
            f"{config.route_prefix}/vault-setup",
        ),
    }
    title, message, action_url = gate_actions.get(
        incomplete_gate,
        ("Continue Setup", f"Complete the '{incomplete_gate}' step to continue.", f"{config.route_prefix}/"),
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — {config.product_name}</title>
<style>
body {{ font-family: Georgia, serif; background: #fdfcfa; color: #1e293b; min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
.card {{ max-width: 450px; background: white; padding: 2.5rem; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); text-align: center; }}
h1 {{ font-size: 1.4rem; color: #1e3a5f; margin-bottom: 1rem; }}
p {{ margin-bottom: 1.5rem; color: #475569; }}
a {{ display: inline-block; background: #1e3a5f; color: white; padding: 0.75rem 2rem; border-radius: 8px; text-decoration: none; }}
a:hover {{ background: #2d5a87; }}
</style></head><body>
<div class="card">
    <h1>{title}</h1>
    <p>{message}</p>
    <a href="{action_url}">Continue</a>
</div>
</body></html>"""
