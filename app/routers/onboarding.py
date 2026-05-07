"""
Semptify 5.0 - Unified Onboarding Router

Single entry point for user progression through gates:
1. storage_connected (OAuth + vault initialized)
2. vault_initialized (vault structure verified)
3. client_activated (first document uploaded)

Sequential, no dead ends, clear feedback at each stage.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Request, Cookie, Query, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.user_id import COOKIE_USER_ID, generate_user_id, parse_user_id
from app.core.config import get_settings
from app.core.navigation import navigation
from app.core.ssot_guard import ssot_redirect
from app.core.user_context import UserRole
from app.models.models import User
from sqlalchemy import select

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
logger = logging.getLogger(__name__)


# ============================================================================
# Smart Entry Point - Detects returning vs new users
# ============================================================================

@router.get("/start")
async def onboarding_entry(
    request: Request,
    semptify_uid: Optional[str] = Cookie(None),
    return_to: Optional[str] = None,
):
    """
    Smart entry point from welcome page.

    - Returning user (has valid semptify_uid cookie) → /storage/reconnect?return_to=...
    - New user (no cookie or invalid cookie) → /onboarding/select-role.html

    Args:
        return_to: Optional URL to return to after reconnect (for task continuation)

    This keeps one CTA on welcome page while routing correctly.
    """
    from app.core.storage_middleware import is_valid_storage_user
    from app.core.checkpoint_middleware import set_checkpoint_cookie

    # Build reconnect URL with return_to if provided
    reconnect_url = "/storage/reconnect"
    if return_to:
        reconnect_url = f"/storage/reconnect?return_to={return_to}"

    # Validate the cookie properly (checks format and signature)
    if semptify_uid and is_valid_storage_user(semptify_uid):
        # Check if session is actually valid before redirecting to reconnect
        # This prevents redirect loops when cookies exist but sessions are invalid
        from app.core.cookie_auth import verify_user_id
        from app.routers.storage import get_valid_session

        raw_uid = verify_user_id(semptify_uid)
        if raw_uid:
            db = request.state.db if hasattr(request.state, 'db') else None
            if db:
                try:
                    session = await get_valid_session(db, raw_uid, auto_refresh=True)
                    if session:
                        # Session valid - go to reconnect flow
                        logger.info(f"Smart entry: returning user {semptify_uid[:4]}... → reconnect (session valid)")
                        response = ssot_redirect(reconnect_url, context="onboarding_entry reconnect")
                        set_checkpoint_cookie(response)
                        return response
                except Exception:
                    pass
        # Session invalid - fall through to new user flow
        logger.info(f"Smart entry: user {semptify_uid[:4]}... has cookie but invalid session → new user flow")

    # New user - set checkpoint server-side and start onboarding (SSOT path)
    logger.info("Smart entry: new user → role selection")
    role_stage = navigation.get_stage("role_select")
    response = ssot_redirect(role_stage.path, context="onboarding_entry role_select")
    set_checkpoint_cookie(response)
    return response


@router.get("/ssot-navigation")
async def get_navigation_ssot():
    """
    Export complete navigation state — SSOT for static files.
    
    Static pages consume this to get canonical paths.
    No hardcoded URLs in HTML/JS.
    """
    return navigation.to_dict()


# Template for role + provider selection
ONBOARDING_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Get Started — Semptify</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        :root {{
            --primary: #1e3a5f;
            --primary-light: #2d5a87;
            --accent: #3b82f6;
            --warm: #f59e0b;
            --text: #1e293b;
            --text-light: #475569;
            --bg: #fdfcfa;
            --paper: #ffffff;
            --border: #e2e8f0;
            --success: #166534;
            --success-bg: #f0fdf4;
            --success-border: #bbf7d0;
        }}

        body {{
            font-family: 'Georgia', 'Times New Roman', serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            line-height: 1.6;
        }}

        .page-header {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
            color: white;
            padding: 2.5rem 2rem;
            text-align: center;
        }}

        .page-header h1 {{
            font-size: 2rem;
            font-weight: 400;
            letter-spacing: -0.02em;
            margin-bottom: 0.25rem;
        }}

        .page-header .subtitle {{
            font-size: 1rem;
            font-weight: 300;
            opacity: 0.85;
            font-style: italic;
        }}

        .page-header .brand {{
            font-size: 0.85rem;
            opacity: 0.65;
            margin-bottom: 0.75rem;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}

        .container {{
            max-width: 680px;
            margin: 0 auto;
            padding: 2rem;
        }}

        .step-indicator {{
            display: flex;
            align-items: center;
            gap: 0;
            margin-bottom: 2rem;
            font-size: 0.85rem;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}

        .step {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
            color: var(--text-light);
        }}

        .step.active {{ color: var(--primary); font-weight: 600; }}
        .step.done {{ color: var(--success); }}

        .step-num {{
            width: 24px;
            height: 24px;
            border-radius: 50%;
            border: 2px solid currentColor;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            flex-shrink: 0;
        }}

        .step.active .step-num {{ background: var(--primary); color: white; border-color: var(--primary); }}
        .step.done .step-num {{ background: var(--success); color: white; border-color: var(--success); }}

        .step-sep {{
            flex: 1;
            height: 2px;
            background: var(--border);
            margin: 0 0.5rem;
        }}

        .step-sep.done {{ background: var(--success); }}

        .card-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}

        @media (max-width: 520px) {{
            .card-grid {{ grid-template-columns: 1fr; }}
        }}

        .role-card {{
            border: 2px solid var(--border);
            border-radius: 10px;
            padding: 1.25rem;
            background: var(--paper);
            cursor: pointer;
            transition: border-color 0.2s, box-shadow 0.2s, transform 0.15s;
            text-align: left;
            position: relative;
            font-family: inherit;
        }}

        .role-card:hover:not(.disabled) {{
            border-color: var(--accent);
            box-shadow: 0 4px 12px rgba(59,130,246,0.12);
            transform: translateY(-2px);
        }}

        .role-card.disabled {{
            opacity: 0.6;
            cursor: not-allowed;
            background: #f8fafc;
        }}

        .role-icon {{
            font-size: 1.75rem;
            margin-bottom: 0.5rem;
            display: block;
        }}

        .role-name {{
            font-size: 1.05rem;
            font-weight: 600;
            color: var(--primary);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            margin-bottom: 0.2rem;
        }}

        .role-desc {{
            font-size: 0.85rem;
            color: var(--text-light);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.4;
        }}

        .badge {{
            display: inline-block;
            font-size: 0.7rem;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-weight: 600;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            margin-top: 0.5rem;
        }}

        .badge-soon {{
            background: #fef3c7;
            color: #92400e;
            border: 1px solid #fde68a;
        }}

        .badge-active {{
            background: var(--success-bg);
            color: var(--success);
            border: 1px solid var(--success-border);
        }}

        .status-box {{
            background: var(--success-bg);
            border: 1px solid var(--success-border);
            border-radius: 8px;
            padding: 0.875rem 1rem;
            margin-bottom: 1.5rem;
            color: var(--success);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 0.9rem;
        }}

        .error-box {{
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 8px;
            padding: 0.875rem 1rem;
            margin-bottom: 1.5rem;
            color: #991b1b;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 0.9rem;
        }}

        .provider-btn {{
            display: flex;
            align-items: center;
            gap: 1rem;
            width: 100%;
            border: 2px solid var(--border);
            border-radius: 10px;
            padding: 1rem 1.25rem;
            background: var(--paper);
            cursor: pointer;
            transition: border-color 0.2s, box-shadow 0.2s;
            text-align: left;
            margin-bottom: 0.75rem;
            font-family: inherit;
        }}

        .provider-btn:hover {{
            border-color: var(--accent);
            box-shadow: 0 4px 12px rgba(59,130,246,0.12);
        }}

        .provider-icon {{ font-size: 1.5rem; flex-shrink: 0; }}

        .provider-name {{
            font-size: 1rem;
            font-weight: 600;
            color: var(--primary);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}

        .provider-desc {{
            font-size: 0.83rem;
            color: var(--text-light);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}

        .section-label {{
            font-size: 0.85rem;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            color: var(--text-light);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 1rem;
            font-weight: 600;
        }}

        .loading {{ text-align: center; padding: 3rem 2rem; }}
        .spinner {{
            display: inline-block;
            width: 32px;
            height: 32px;
            border: 3px solid var(--border);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}

        .footer-note {{
            margin-top: 2.5rem;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border);
            font-size: 0.8rem;
            color: var(--text-light);
            text-align: center;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}
    </style>
</head>
<body>
    <div class="page-header">
        <div class="brand">Semptify</div>
        <h1>__HEADER_TITLE__</h1>
        <p class="subtitle">__HEADER_SUBTITLE__</p>
    </div>
    <div class="container">
        __CONTENT__
        <div class="footer-note">
            Free forever &middot; No advertising &middot; Privacy-first &middot; Not legal advice
        </div>
    </div>
</body>
</html>
"""


def _render_page(content: str, header_title: str = "Get Started", header_subtitle: str = "Protecting your housing rights.") -> str:
    """Render an onboarding page using the shared template."""
    return (
        ONBOARDING_TEMPLATE
        .replace("__HEADER_TITLE__", header_title)
        .replace("__HEADER_SUBTITLE__", header_subtitle)
        .replace("__CONTENT__", content)
    )

def _render_role_selection():
    """Role Selection Page with all 6 roles"""
    return _render_page(
        header_title="Who are you here for?",
        header_subtitle="Protecting housing rights, one record at a time.",
        content="""
        <div class="step-indicator">
            <div class="step active">
                <div class="step-num">1</div>
                <span>Your Role</span>
            </div>
            <div class="step-sep"></div>
            <div class="step">
                <div class="step-num">2</div>
                <span>Connect Storage</span>
            </div>
            <div class="step-sep"></div>
            <div class="step">
                <div class="step-num">3</div>
                <span>First Document</span>
            </div>
        </div>

        <p class="section-label">Select your role to get started</p>

        <div class="card-grid">
            <button class="role-card" onclick="selectRole('tenant')">
                <span class="role-icon">🏠</span>
                <div class="role-name">Tenant</div>
                <div class="role-desc">Organize your own housing case, documents, and evidence.</div>
                <span class="badge badge-active">Available now</span>
            </button>

            <button class="role-card disabled" disabled>
                <span class="role-icon">🤝</span>
                <div class="role-name">Advocate</div>
                <div class="role-desc">Support multiple clients and manage cases on their behalf.</div>
                <span class="badge badge-soon">Coming soon</span>
            </button>

            <button class="role-card disabled" disabled>
                <span class="role-icon">⚖️</span>
                <div class="role-name">Legal Professional</div>
                <div class="role-desc">Attorney or legal aid worker with multi-case access.</div>
                <span class="badge badge-soon">Coming soon</span>
            </button>

            <button class="role-card disabled" disabled>
                <span class="role-icon">👨‍⚖️</span>
                <div class="role-name">Judge / Mediator</div>
                <div class="role-desc">Neutral review and dispute resolution tools.</div>
                <span class="badge badge-soon">Coming soon</span>
            </button>

            <button class="role-card disabled" disabled>
                <span class="role-icon">📋</span>
                <div class="role-name">Property Manager</div>
                <div class="role-desc">Manage tenant relations and maintenance records.</div>
                <span class="badge badge-soon">Coming soon</span>
            </button>

            <button class="role-card disabled" disabled>
                <span class="role-icon">🔧</span>
                <div class="role-name">System Admin</div>
                <div class="role-desc">Platform administration and oversight tools.</div>
                <span class="badge badge-soon">Coming soon</span>
            </button>
        </div>

        <script>
        function selectRole(role) {
            localStorage.setItem('selectedRole', role);
            window.location.href = '/onboarding/providers?role=' + role;
        }
        </script>
    """)

def _render_storage_selection():
    """Step 2: Storage Provider Selection"""
    settings = get_settings()

    providers_html = ""

    if settings.google_drive_client_id:
        providers_html += """
        <button class="provider-btn" onclick="selectProvider('google_drive')">
            <span class="provider-icon">📁</span>
            <div>
                <div class="provider-name">Google Drive</div>
                <div class="provider-desc">Store documents in your Google account</div>
            </div>
        </button>
        """

    if settings.dropbox_app_key:
        providers_html += """
        <button class="provider-btn" onclick="selectProvider('dropbox')">
            <span class="provider-icon">☁️</span>
            <div>
                <div class="provider-name">Dropbox</div>
                <div class="provider-desc">Store documents in your Dropbox account</div>
            </div>
        </button>
        """

    if settings.onedrive_client_id:
        providers_html += """
        <button class="provider-btn" onclick="selectProvider('onedrive')">
            <span class="provider-icon">🔵</span>
            <div>
                <div class="provider-name">OneDrive</div>
                <div class="provider-desc">Store documents in your Microsoft account</div>
            </div>
        </button>
        """

    if not providers_html:
        providers_html = """
        <div class="error-box">
            No storage providers are configured. Please contact support.
        </div>
        """

    return _render_page(
        header_title="Connect your storage",
        header_subtitle="Your documents stay in your account — we never store them.",
        content=f"""
        <div class="step-indicator">
            <div class="step done">
                <div class="step-num">✓</div>
                <span>Your Role</span>
            </div>
            <div class="step-sep done"></div>
            <div class="step active">
                <div class="step-num">2</div>
                <span>Connect Storage</span>
            </div>
            <div class="step-sep"></div>
            <div class="step">
                <div class="step-num">3</div>
                <span>First Document</span>
            </div>
        </div>

        <div class="status-box">&#10003; Role selected. Choose where to store your documents securely.</div>

        <p class="section-label">Choose a storage provider</p>

        {providers_html}

        <script>
        function selectProvider(provider) {{
            const role = new URLSearchParams(window.location.search).get('role') || 'tenant';
            window.location.href = '/onboarding/connect?provider=' + provider + '&role=' + role;
        }}
        </script>
    """)

def _render_connecting():
    """Step 3: Connecting (redirect to OAuth)"""
    return _render_page(content="""
        <div class="loading">
            <div class="spinner"></div>
            <p style="margin-top: 1.5rem; font-family: sans-serif;">Redirecting to your storage provider...</p>
        </div>
        <div class="status-box" style="margin-top: 2rem;">
            You will be asked to authorize Semptify to access your storage.
        </div>""",
        header_title="Connecting...",
        header_subtitle="Setting up your storage connection.",
    )

def _render_storage_connected():
    """Gate 1: storage_connected ✓"""
    return _render_page(header_title="Storage Connected", header_subtitle="Your vault is ready.", content="""
        <div class="status-box" style="margin-bottom:1.5rem;">&#10003; Gate 1 of 3 complete — storage authenticated and secure.</div>

        <button class="provider-btn" onclick="window.location.href='/onboarding/upload'">
            <span class="provider-icon">📄</span>
            <div>
                <div class="provider-name">Upload Your First Document</div>
                <div class="provider-desc">This activates your workspace</div>
            </div>
        </button>

        <p style="font-size:0.82rem;color:var(--text-light);text-align:center;margin-top:1.5rem;font-family:sans-serif;">
            Semptify stores only your encrypted token. Your documents stay in your account.
        </p>

    """)

def _render_vault_initialized():
    """Gate 2: vault_initialized ✓"""
    return _render_page(header_title="Vault Ready", header_subtitle="Your secure workspace is verified.", content="""
        <div class="progress">
            <div class="progress-dot active"></div>
            <div class="progress-dot active"></div>
            <div class="progress-dot active"></div>
        </div>
        
        <h1>✓ Vault Initialized!</h1>
        <p class="subtitle">Your secure workspace is ready</p>
        
        <div class="status-box">
            <strong>Gate 2/3 Complete:</strong> vault_initialized ✓<br>
            Your vault structure is verified and ready for documents.
        </div>
        
        <div class="step-section">
            <p style="margin-bottom: 1.5rem;">You can now upload documents to activate your account.</p>
            <button class="btn" onclick="window.location.href='/upload'" style="width: 100%; padding: 1.5rem;">
                📤 Go to Document Upload
            </button>
        </div>
    """)

def _render_simple_onboarding():
    """Simplified linear onboarding flow."""
    return _render_page(content="""
        <div class="progress">
            <div class="progress-fill" id="progress_fill"></div>
        </div>
        
        <!-- Step 1: Welcome -->
        <div class="step active" id="step1">
            <h1>🏠 Welcome to Semptify</h1>
            <p class="subtitle">Protect your housing rights with organized evidence</p>
            
            <button class="btn btn-primary" onclick="nextStep()">
                Get Started →
            </button>
        </div>
        
        <!-- Step 2: Role Selection -->
        <div class="step" id="step2">
            <h1>What best describes you?</h1>
            <p class="subtitle">We'll customize your experience based on your role</p>
            
            <button class="btn" onclick="selectRole('tenant')">
                <strong>🏠 I'm a Tenant</strong>
                <div style="font-size: 0.875rem; opacity: 0.8; margin-top: 0.25rem;">
                    Organizing my own case
                </div>
            </button>
            
            <button class="btn" onclick="selectRole('advocate')">
                <strong>🤝 I'm an Advocate</strong>
                <div style="font-size: 0.875rem; opacity: 0.8; margin-top: 0.25rem;">
                    Helping multiple clients
                </div>
            </button>
            
            <button class="btn" onclick="selectRole('legal')">
                <strong>⚖️ I'm Legal/Judge</strong>
                <div style="font-size: 0.875rem; opacity: 0.8; margin-top: 0.25rem;">
                    Professional review role
                </div>
            </button>
        </div>
        
        <!-- Step 3: Storage Connection -->
        <div class="step" id="step3">
            <h1>☁️ Connect Your Storage</h1>
            <p class="subtitle">Choose where to store your documents securely</p>
            
            <div id="storage_options">
                <!-- Storage options will be loaded here -->
            </div>
            
            <button class="btn" onclick="previousStep()">
                ← Back
            </button>
        </div>
        
        <!-- Step 4: Connecting -->
        <div class="step" id="step4">
            <h1>Connecting...</h1>
            <p class="subtitle">Setting up your secure storage connection</p>
            
            <div class="loading">
                <div class="spinner"></div>
                <p>Authorizing with your storage provider...</p>
            </div>
        </div>
        
        <!-- Step 5: Complete -->
        <div class="step" id="step5">
            <h1>✅ All Set!</h1>
            <p class="subtitle">Your vault is ready to use</p>
            
            <button class="btn btn-primary" onclick="goToDashboard()">
                Go to Dashboard →
            </button>
        </div>
        
        <!-- Error State -->
        <div class="step" id="error_step" style="display: none;">
            <h1>❌ Something went wrong</h1>
            <p class="subtitle">Please try again or contact support</p>
            
            <div class="error" id="error_message">
                <!-- Error message will be shown here -->
            </div>
            
            <button class="btn" onclick="retryStep()">
                Try Again
            </button>
        </div>
    </div>
    
    <script>
        let currentStep = 1;
        let selectedRole = null;
        let selectedProvider = null;
        
        function updateProgress() {
            const progressFill = document.getElementById('progress_fill');
            const percentage = (currentStep / 5) * 100;
            progressFill.style.width = percentage + '%';
        }
        
        function showStep(stepNumber) {
            // Hide all steps
            document.querySelectorAll('.step').forEach(step => {
                step.classList.remove('active');
            });
            
            // Show current step
            const currentStepElement = document.getElementById('step' + stepNumber);
            if (currentStepElement) {
                currentStepElement.classList.add('active');
            }
            
            currentStep = stepNumber;
            updateProgress();
        }
        
        function nextStep() {
            if (currentStep < 5) {
                showStep(currentStep + 1);
            }
        }
        
        function previousStep() {
            if (currentStep > 1) {
                showStep(currentStep - 1);
            }
        }
        
        function selectRole(role) {
            selectedRole = role;
            loadStorageOptions();
            nextStep();
        }
        
        function loadStorageOptions() {
            const storageOptions = document.getElementById('storage_options');
            
            // Fetch available storage providers
            fetch('/api/storage/providers')
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.providers) {
                        let optionsHtml = '';
                        
                        data.providers.forEach(provider => {
                            optionsHtml += `
                                <button class="btn" onclick="selectProvider('${provider.id}')">
                                    <strong>${provider.name}</strong>
                                    <div style="font-size: 0.875rem; opacity: 0.8; margin-top: 0.25rem;">
                                        ${provider.description}
                                    </div>
                                </button>
                            `;
                        });
                        
                        storageOptions.innerHTML = optionsHtml;
                    } else {
                        showError('Failed to load storage providers');
                    }
                })
                .catch(error => {
                    console.error('Failed to load storage providers:', error);
                    showError('Failed to connect to storage services');
                });
        }
        
        function selectProvider(providerId) {
            selectedProvider = providerId;
            nextStep();
        }
        
        function connectStorage() {
            showStep(4);
            
            // Initiate OAuth flow
            const connectUrl = `/storage/connect?provider=${selectedProvider}&role=${selectedRole}`;
            window.location.href = connectUrl;
        }
        
        function goToDashboard() {
            const dashboardUrl = `/${selectedRole}/dashboard`;
            window.location.href = dashboardUrl;
        }
        
        function showError(message) {
            const errorStep = document.getElementById('error_step');
            const errorMessage = document.getElementById('error_message');
            
            errorMessage.textContent = message;
            showStep('error');
        }
        
        function retryStep() {
            showStep(1);
        }
        
        // Auto-advance when storage provider is selected
        document.addEventListener('DOMContentLoaded', function() {
            // Check URL parameters for auto-advancement
            const urlParams = new URLSearchParams(window.location.search);
            const role = urlParams.get('role');
            const provider = urlParams.get('provider');
            
            if (role && provider) {
                selectedRole = role;
                selectedProvider = provider;
                showStep(4); // Show connecting state
            }
        });
        
        // Handle step 3 auto-advance
        const originalNextStep = nextStep;
        nextStep = function() {
            if (currentStep === 3 && selectedProvider) {
                connectStorage();
            } else {
                originalNextStep();
            }
        };
    </script>
    """)

def _render_client_activated():
    """Gate 3: client_activated ✓"""
    return _render_page(header_title="You're All Set!", header_subtitle="All activation gates complete.", content="""
        <div class="progress">
            <div class="progress-dot active"></div>
            <div class="progress-dot active"></div>
            <div class="progress-dot active"></div>
        </div>
        
        <h1>🎉 You're All Set!</h1>
        <p class="subtitle">All activation gates complete</p>
        
        <div class="status-box">
            <strong>Gate 3/3 Complete:</strong> client_activated ✓<br>
            You're now a full Semptify client with access to all tools.
        </div>
        
        <div class="step-section">
            <button class="btn" onclick="window.location.href='/ui/route'" style="width: 100%; padding: 1.5rem; font-size: 1.1rem;">
                ✓ Enter Semptify
            </button>
        </div>
        
        <div style="color: #a7f3d0; font-size: 0.9rem; margin-top: 2rem; text-align: center;">
            Your evidence is protected, organized, and ready for any situation.
        </div>
    """)

# ============================================================================
# ROUTES
# ============================================================================

@router.get("/", response_class=HTMLResponse)
async def onboarding_root(request: Request, semptify_uid: Optional[str] = Cookie(None)):
    """Entry point: Show role selection OR route based on gate status."""
    # Use SSOT navigation registry
    if not semptify_uid:
        role_stage = navigation.get_stage("role_select")
        return ssot_redirect(role_stage.path, context="onboarding_root role_select")
    else:
        return ssot_redirect("/onboarding/status", context="onboarding_root status")

@router.get("/role-select")
async def role_select_redirect():
    """Legacy redirect - routes to SSOT role selection."""
    role_stage = navigation.get_stage("role_select")
    return ssot_redirect(role_stage.path, context="role_select_redirect")

@router.get("/select-role.html")
async def role_select_static():
    """
    Generate role selection page HTML dynamically.
    
    Static file removed due to conflicts - router generates HTML now.
    """
    return HTMLResponse(content=_render_role_selection())

@router.get("/providers", response_class=HTMLResponse)
async def storage_providers(role: Optional[str] = Query("tenant")):
    """Show storage provider selection."""
    return HTMLResponse(content=_render_storage_selection())

@router.get("/connect")
async def connect_storage(provider: str = Query(...), role: str = Query("tenant")):
    """Redirect to OAuth flow."""
    auth_url = f"/storage/auth/{provider}?role={role}&from=onboarding"
    return ssot_redirect(auth_url, context="connect_storage oauth")

@router.get("/status", response_class=HTMLResponse)
async def onboarding_status(semptify_uid: Optional[str] = Cookie(None), db: AsyncSession = Depends(get_db)):
    """Check current gate status and show appropriate message."""
    if not semptify_uid:
        return ssot_redirect("/onboarding/", context="onboarding_status no cookie")

    result = await db.execute(select(User).where(User.id == semptify_uid))
    user = result.scalar_one_or_none()

    if not user:
        return ssot_redirect("/onboarding/", context="onboarding_status no user")

    completed = (user.completed_groups or "").split(",")

    if "client_activated" in completed:
        return HTMLResponse(content=_render_client_activated())
    elif "vault_initialized" in completed:
        return HTMLResponse(content=_render_vault_initialized())
    elif "storage_connected" in completed:
        return HTMLResponse(content=_render_storage_connected())
    else:
        # User exists but hasn't connected storage - go to storage entry (not back to /onboarding)
        # This prevents redirect loop: /onboarding/ -> /onboarding/status -> /onboarding/
        return ssot_redirect("/storage/entry", context="onboarding_status needs storage")

@router.get("/upload", response_class=HTMLResponse)
async def upload_prompt(semptify_uid: Optional[str] = Cookie(None)):
    """Prompt new user to upload first document to activate vault and account."""
    if not semptify_uid:
        return ssot_redirect("/onboarding/", context="upload_prompt no cookie")

    return HTMLResponse(content=_render_page(header_title="Add Your First Document", header_subtitle="This activates your workspace.", content="""
        <div class="progress">
            <div class="progress-dot active"></div>
            <div class="progress-dot active"></div>
            <div class="progress-dot"></div>
        </div>

        <h1>📄 Add Your First Document</h1>
        <p class="subtitle">This verifies your vault is working and activates your account</p>

        <div class="status-box">
            ✓ Storage connected. Upload one document to confirm your vault is ready.<br>
            This can be anything — a lease, a notice, a photo. You can add more later.
        </div>

        <div class="step-section" style="margin-top: 2rem;">
            <form id="uploadForm" enctype="multipart/form-data">
                <input type="file" id="fileInput" name="file" required
                    aria-label="Choose a document to upload"
                    style="padding: 1rem; width: 100%; margin-bottom: 1rem;
                           background: rgba(255,255,255,0.1); border-radius: 8px; color: #fff;">
                <button type="submit" class="btn" style="width: 100%; padding: 1rem; cursor: pointer;">
                    📤 Upload &amp; Activate
                </button>
            </form>
            <div id="uploadStatus" style="margin-top: 1rem;"></div>
        </div>

        <script>
        // Step sequence: upload → verify vault → activate → route
        // Onboarding complete signal fires ONLY after vault confirms the doc is stored.

        function setStatus(msg, color) {
            document.getElementById('uploadStatus').innerHTML =
                '<p style="color:' + color + '; margin-top:0.5rem;">' + msg + '</p>';
        }

        async function verifyVault(docId, attempts) {
            // Polls verify-vault up to `attempts` times with 1.5s gap.
            // Returns true if confirmed, false if all attempts fail.
            for (let i = 0; i < attempts; i++) {
                if (i > 0) {
                    setStatus('⏳ Confirming vault storage... (' + i + '/' + attempts + ')', '#a7f3d0');
                    await new Promise(r => setTimeout(r, 1500));
                }
                try {
                    const r = await fetch('/onboarding/verify-vault?doc_id=' + encodeURIComponent(docId));
                    const data = await r.json();
                    if (data.ok) return { ok: true };
                    // Surface the exact reason from the server on final attempt
                    if (i === attempts - 1) return { ok: false, reason: data.reason };
                } catch (e) {
                    if (i === attempts - 1) return { ok: false, reason: 'Connection error during vault check.' };
                }
            }
            return { ok: false, reason: 'Vault did not confirm in time.' };
        }

        document.getElementById('uploadForm').onsubmit = async (e) => {
            e.preventDefault();
            const file = document.getElementById('fileInput').files[0];
            if (!file) return;

            const submitBtn = e.target.querySelector('button[type="submit"]');
            submitBtn.disabled = true;

            // Step 1: Upload
            setStatus('📤 Uploading...', '#a7f3d0');
            const formData = new FormData();
            formData.append('file', file);

            let docId;
            try {
                const res = await fetch('/api/documents/upload', { method: 'POST', body: formData });
                if (!res.ok) {
                    let errBody = {};
                    try { errBody = await res.json(); } catch (_) { errBody = { message: await res.text() }; }
                    console.error('Upload error:', errBody);
                    if (res.status === 401 && errBody.redirect_url) {
                        setStatus('Session expired — redirecting to reconnect...', '#fcd34d');
                        setTimeout(() => { window.location.href = errBody.redirect_url; }, 1200);
                        return;
                    }
                    setStatus('Upload failed: ' + (errBody.message || res.status), '#fca5a5');
                    submitBtn.disabled = false;
                    return;
                }
                const data = await res.json();
                // Extract vault_id from response — field may be vault_id or doc_id
                docId = data.vault_id || data.doc_id || data.id || null;
            } catch (err) {
                setStatus('Connection error during upload. Please try again.', '#fca5a5');
                console.error(err);
                submitBtn.disabled = false;
                return;
            }

            if (!docId) {
                setStatus('Upload succeeded but no document ID was returned. Please contact support.', '#fca5a5');
                console.warn('Upload response had no vault_id/doc_id/id field:', data);
                submitBtn.disabled = false;
                return;
            }

            // Step 2: Verify vault — confirm the doc is actually stored before proceeding
            setStatus('✓ Upload received — verifying vault storage...', '#a7f3d0');
            const verify = await verifyVault(String(docId), 5);

            if (!verify.ok) {
                setStatus(
                    '⚠ Vault check failed: ' + verify.reason +
                    '<br><small>Your upload was received but storage could not be confirmed. ' +
                    'Please try uploading again.</small>',
                    '#fcd34d'
                );
                submitBtn.disabled = false;
                return;
            }

            // Step 3: All checks passed — fire the onboarding complete signal
            setStatus('✓ Vault confirmed — activating your account...', '#a7f3d0');
            try {
                await fetch('/onboarding/activate', { method: 'POST' });
            } catch (err) {
                console.warn('Activate call failed (non-fatal):', err);
            }

            setStatus('✓ Account activated — entering Semptify...', '#10b981');
            window.location.href = '/ui/route';
        };
        </script>
    """))


@router.get("/verify-vault")
async def verify_vault(
    doc_id: str = Query(..., description="vault_id returned by the upload endpoint"),
    semptify_uid: Optional[str] = Cookie(None),
):
    """
    Vault readiness check — called BEFORE the onboarding complete signal fires.

    Confirms:
    1. The vault service is reachable
    2. The uploaded document is indexed under this user (by vault_id)
    3. The storage path on the document record is non-empty

    Returns JSON: { ok: bool, reason: str }
    The upload page must receive ok=true before calling /onboarding/activate.
    """
    if not semptify_uid:
        return JSONResponse({"ok": False, "reason": "Not authenticated — no session cookie."})

    if not doc_id:
        return JSONResponse({"ok": False, "reason": "No document ID supplied."})

    try:
        from app.services.vault_upload_service import get_vault_service
        svc = get_vault_service()

        # Check 1: vault service is alive
        try:
            docs = svc.get_user_documents(semptify_uid)
        except Exception as exc:
            logger.error("verify-vault: get_user_documents failed: %s", exc)
            return JSONResponse({
                "ok": False,
                "reason": "Vault service could not be reached. Try again in a moment.",
            })

        # Check 2: the specific doc_id is present and belongs to this user
        match = next((d for d in docs if getattr(d, "vault_id", None) == doc_id), None)
        if not match:
            logger.warning(
                "verify-vault: doc_id=%s not found in vault for user=%s",
                doc_id[:8] + "***",
                semptify_uid[:6] + "***",
            )
            return JSONResponse({
                "ok": False,
                "reason": "Document not found in your vault yet. The upload may still be processing — please wait a moment and try again.",
            })

        # Check 3: storage path is recorded (document reached the storage layer)
        if not getattr(match, "storage_path", None):
            logger.warning(
                "verify-vault: doc_id=%s has no storage_path for user=%s",
                doc_id[:8] + "***",
                semptify_uid[:6] + "***",
            )
            return JSONResponse({
                "ok": False,
                "reason": "Document was received but the storage path was not confirmed. Please try uploading again.",
            })

        logger.info(
            "verify-vault: PASS for user=%s doc_id=%s path=%s",
            semptify_uid[:6] + "***",
            doc_id[:8] + "***",
            str(match.storage_path)[:40],
        )
        return JSONResponse({"ok": True, "reason": "Vault confirmed. Document is stored and retrievable."})

    except Exception as exc:
        logger.exception("verify-vault: unexpected error: %s", exc)
        return JSONResponse({
            "ok": False,
            "reason": "Verification check encountered an unexpected error. Please try again.",
        })


@router.post("/activate")
async def activate_client(
    semptify_uid: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """Mark client_activated gate complete. Called after verify-vault passes."""
    if not semptify_uid:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(select(User).where(User.id == semptify_uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    completed = set((user.completed_groups or "").split(","))
    completed.discard("")
    completed.add("vault_initialized")
    completed.add("client_activated")
    user.completed_groups = ",".join(sorted(completed))
    await db.commit()

    logger.info("client_activated gate set for user=%s", semptify_uid[:6] + "***")
    return {"ok": True}
