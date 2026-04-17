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
from app.core.user_context import UserRole
from app.models.models import User
from sqlalchemy import select

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
logger = logging.getLogger(__name__)

# Template for role + provider selection
ONBOARDING_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Get Started with Semptify</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #064e3b 0%, #065f46 100%);
            color: #fff;
            min-height: 100vh;
            padding: 2rem;
        }}
        
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 2rem;
            backdrop-filter: blur(10px);
        }}
        
        h1 {{ margin-bottom: 0.5rem; font-size: 2rem; }}
        .subtitle {{ color: #a7f3d0; margin-bottom: 2rem; }}
        
        .step-section {{ margin-bottom: 2rem; }}
        .step-title {{ font-size: 1.2rem; font-weight: 600; margin-bottom: 1rem; }}
        
        .button-grid {{
            display: grid;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        
        .btn {{
            padding: 1rem;
            border: 2px solid transparent;
            border-radius: 8px;
            background: rgba(255,255,255,0.1);
            color: #fff;
            cursor: pointer;
            transition: all 0.3s;
            text-align: left;
            font-size: 1rem;
        }}
        
        .btn:hover {{
            background: rgba(255,255,255,0.15);
            border-color: #10b981;
            transform: translateX(4px);
        }}
        
        .btn-icon {{ font-size: 1.5rem; margin-right: 1rem; }}
        .btn-label {{ font-weight: 600; }}
        .btn-desc {{ font-size: 0.9rem; color: #a7f3d0; margin-top: 0.25rem; }}
        
        .progress {{
            display: flex;
            gap: 0.5rem;
            margin-bottom: 2rem;
        }}
        
        .progress-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: rgba(255,255,255,0.3);
        }}
        
        .progress-dot.active {{ background: #10b981; }}
        
        .status-box {{
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid #10b981;
            border-radius: 8px;
            padding: 1rem;
            margin: 1.5rem 0;
            color: #d1fae5;
        }}
        
        .error-box {{
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid #ef4444;
            border-radius: 8px;
            padding: 1rem;
            margin: 1.5rem 0;
            color: #fca5a5;
        }}
        
        .loading {{ text-align: center; padding: 2rem; }}
        .spinner {{
            display: inline-block;
            width: 30px;
            height: 30px;
            border: 3px solid rgba(255,255,255,0.3);
            border-top-color: #10b981;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    </style>
</head>
<body>
    <div class="container">
        {content}
    </div>
</body>
</html>
"""

def _render_welcome_and_roles():
    """Step 1: Welcome + Role Selection"""
    return ONBOARDING_TEMPLATE.format(content="""
        <div class="progress">
            <div class="progress-dot active"></div>
            <div class="progress-dot"></div>
            <div class="progress-dot"></div>
        </div>
        
        <h1>🏠 Welcome to Semptify</h1>
        <p class="subtitle">Protect your housing rights with organized evidence</p>
        
        <div class="step-section">
            <p style="margin-bottom: 1.5rem;">What best describes you?</p>
            
            <div class="button-grid">
                <button class="btn" onclick="selectRole('user')">
                    <span class="btn-icon">🏠</span>
                    <div>
                        <div class="btn-label">I'm a Tenant</div>
                        <div class="btn-desc">Organizing my own case</div>
                    </div>
                </button>
                
                <button class="btn" onclick="selectRole('advocate')">
                    <span class="btn-icon">🤝</span>
                    <div>
                        <div class="btn-label">I'm an Advocate</div>
                        <div class="btn-desc">Helping multiple clients</div>
                    </div>
                </button>
                
                <button class="btn" onclick="selectRole('legal')">
                    <span class="btn-icon">⚖️</span>
                    <div>
                        <div class="btn-label">I'm Legal/Judge</div>
                        <div class="btn-desc">Professional review role</div>
                    </div>
                </button>
            </div>
        </div>
        
        <script>
        function selectRole(role) {{
            window.location.href = '/onboarding/providers?role=' + role;
        }}
        </script>
    """)

def _render_storage_selection():
    """Step 2: Storage Provider Selection"""
    settings = get_settings()
    
    providers_html = ""
    
    if settings.google_drive_client_id:
        providers_html += """
        <button class="btn" onclick="selectProvider('google_drive')">
            <span class="btn-icon">📁</span>
            <div>
                <div class="btn-label">Google Drive</div>
                <div class="btn-desc">Connect your Google account</div>
            </div>
        </button>
        """
    
    if settings.dropbox_app_key:
        providers_html += """
        <button class="btn" onclick="selectProvider('dropbox')">
            <span class="btn-icon">☁️</span>
            <div>
                <div class="btn-label">Dropbox</div>
                <div class="btn-desc">Connect your Dropbox account</div>
            </div>
        </button>
        """
    
    if settings.onedrive_client_id:
        providers_html += """
        <button class="btn" onclick="selectProvider('onedrive')">
            <span class="btn-icon">🔵</span>
            <div>
                <div class="btn-label">OneDrive</div>
                <div class="btn-desc">Connect your Microsoft account</div>
            </div>
        </button>
        """
    
    return ONBOARDING_TEMPLATE.format(content=f"""
        <div class="progress">
            <div class="progress-dot active"></div>
            <div class="progress-dot active"></div>
            <div class="progress-dot"></div>
        </div>
        
        <h1>☁️ Connect Storage</h1>
        <p class="subtitle">Choose where to store your documents securely</p>
        
        <div class="status-box">
            ✓ Role selected. Now connect your cloud storage.
        </div>
        
        <div class="step-section">
            <div class="button-grid">
                {providers_html}
            </div>
        </div>
        
        <script>
        function selectProvider(provider) {{
            const role = new URLSearchParams(window.location.search).get('role') || 'user';
            window.location.href = '/onboarding/connect?provider=' + provider + '&role=' + role;
        }}
        </script>
    """)

def _render_connecting():
    """Step 3: Connecting (redirect to OAuth)"""
    return ONBOARDING_TEMPLATE.format(content="""
        <div class="progress">
            <div class="progress-dot active"></div>
            <div class="progress-dot active"></div>
            <div class="progress-dot"></div>
        </div>
        
        <h1>Connecting...</h1>
        <p class="subtitle">Setting up your storage connection</p>
        
        <div class="loading">
            <div class="spinner"></div>
            <p style="margin-top: 1.5rem;">Redirecting to your storage provider...</p>
        </div>
        
        <div class="status-box" style="margin-top: 2rem;">
            You'll be asked to authorize Semptify to access your storage.
        </div>
    """)

def _render_storage_connected():
    """Gate 1: storage_connected ✓"""
    return ONBOARDING_TEMPLATE.format(content="""
        <div class="progress">
            <div class="progress-dot active"></div>
            <div class="progress-dot active"></div>
            <div class="progress-dot active"></div>
        </div>
        
        <h1>✓ Storage Connected!</h1>
        <p class="subtitle">Your vault is ready</p>
        
        <div class="status-box">
            <strong>Gate 1/3 Complete:</strong> storage_connected ✓<br>
            Your storage account is authenticated and secure.
        </div>
        
        <div class="step-section">
            <p style="margin-bottom: 1.5rem;">What's next?</p>
            <button class="btn" onclick="window.location.href='/onboarding/upload'" style="width: 100%;">
                📄 Upload Your First Document
                <div class="btn-desc" style="margin-top: 0.5rem;">This activates your workspace</div>
            </button>
        </div>
        
        <div style="color: #a7f3d0; font-size: 0.9rem; margin-top: 2rem; text-align: center;">
            Semptify is securely storing your connection. Your documents are yours alone.
        </div>
    """)

def _render_vault_initialized():
    """Gate 2: vault_initialized ✓"""
    return ONBOARDING_TEMPLATE.format(content="""
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
    return ONBOARDING_TEMPLATE.format(content="""
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
    return ONBOARDING_TEMPLATE.format(content="""
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
            <button class="btn" onclick="window.location.href='/ui/'" style="width: 100%; padding: 1.5rem; font-size: 1.1rem;">
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
async def onboarding_start(request: Request, semptify_uid: Optional[str] = Cookie(None)):
    """Entry point: Show welcome + role selection OR route based on gate status."""
    if not semptify_uid:
        return HTMLResponse(content=_render_welcome_and_roles())
    elif "vault_initialized" in completed:
        return HTMLResponse(content=_render_vault_initialized())
    elif "storage_connected" in completed:
        return HTMLResponse(content=_render_storage_connected())
    else:
        return HTMLResponse(content=_render_welcome_and_roles())

@router.get("/providers", response_class=HTMLResponse)
async def storage_providers(role: Optional[str] = Query("user")):
    """Show storage provider selection."""
    return HTMLResponse(content=_render_storage_selection())

@router.get("/connect")
async def connect_storage(provider: str = Query(...), role: str = Query("user")):
    """Redirect to OAuth flow."""
    return RedirectResponse(
        url=f"/storage/auth/{provider}?role={role}&from=onboarding&return_to=/onboarding/status",
        status_code=302
    )

@router.get("/status", response_class=HTMLResponse)
async def onboarding_status(semptify_uid: Optional[str] = Cookie(None), db: AsyncSession = Depends(get_db)):
    """Check current gate status and show appropriate message."""
    if not semptify_uid:
        return RedirectResponse(url="/onboarding", status_code=302)
    
    result = await db.execute(select(User).where(User.id == semptify_uid))
    user = result.scalar_one_or_none()
    
    if not user:
        return RedirectResponse(url="/onboarding", status_code=302)
    
    completed = (user.completed_groups or "").split(",")
    
    if "client_activated" in completed:
        return HTMLResponse(content=_render_client_activated())
    elif "vault_initialized" in completed:
        return HTMLResponse(content=_render_vault_initialized())
    elif "storage_connected" in completed:
        return HTMLResponse(content=_render_storage_connected())
    else:
        return RedirectResponse(url="/onboarding", status_code=302)

@router.get("/upload", response_class=HTMLResponse)
async def upload_prompt(semptify_uid: Optional[str] = Cookie(None)):
    """Prompt user to upload first document."""
    if not semptify_uid:
        return RedirectResponse(url="/onboarding", status_code=302)
    
    return HTMLResponse(content=ONBOARDING_TEMPLATE.format(content="""
        <h1>📄 Upload Your First Document</h1>
        <p class="subtitle">This activates client_activated gate</p>
        
        <div class="status-box">
            Uploading your first document completes account activation.<br>
            After this, you'll have access to all Semptify features.
        </div>
        
        <div class="step-section" style="margin-top: 2rem;">
            <form id="uploadForm" enctype="multipart/form-data">
                <input type="file" id="fileInput" name="file" required style="
                    padding: 1rem; width: 100%; margin-bottom: 1rem;
                    background: rgba(255,255,255,0.1); border-radius: 8px; color: #fff;
                ">
                <button type="submit" class="btn" style="width: 100%; padding: 1rem; cursor: pointer;">
                    📤 Upload Document
                </button>
            </form>
        </div>
        
        <script>
        document.getElementById('uploadForm').onsubmit = async (e) => {
            e.preventDefault();
            const file = document.getElementById('fileInput').files[0];
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch('/documents/upload', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                window.location.href = '/onboarding/status';
            } else {
                alert('Upload failed');
            }
        };
        </script>
    """))
