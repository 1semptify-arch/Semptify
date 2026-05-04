# Semptify Current State Map
**Generated:** May 3, 2026  
**Focus:** Tenant Role Only | Jinja2 + Static Hybrid  
**Status:** Onboarding/Reconnect Broken - In Repair

---

## The Original Plan (What You Wanted)

```
User visits / → Jinja2 welcome.html (with static fallback)
         ↓
    Click "Get Started"
         ↓
    /onboarding/start (router decides)
         ↓
    NEW USER → Jinja2 select-role.html
         ↓
    /onboarding/storage (Jinja2)
         ↓
    OAuth → Jinja2 tenant_home.html
         ↓
    /tenant/vault (Jinja2) → Upload works

    RETURNING USER → /storage/reconnect (router)
         ↓
    Check cookie → Valid → Jinja2 tenant_home.html
         ↓
    Invalid → Silent OAuth → Jinja2 tenant_home.html
```

**What Broke:** Welcome page → Reconnect flow connection

---

## CURRENT REALITY: Two Competing Systems

### System A: Static HTML (Currently Serving)

| File | URL | Status | Problem |
|------|-----|--------|---------|
| `static/public/welcome.html` | `/static/public/welcome.html` | ✅ Works | But calls `/onboarding/start` |
| `static/onboarding/index.html` | `/onboarding/` | ❌ BROKEN | Meta-refresh to `select-role.html` (bypasses router) |
| `static/onboarding/select-role.html` | `/onboarding/select-role.html` | ⚠️ CONFLICT | Static file exists, router also serves it |
| `static/home.html` | `/home.html` | ✅ Works | But shows stats as "0" (no backend) |

**Issue:** Static files bypass Jinja2 context, can't use SSOT navigation API

### System B: Jinja2 Templates (Exists But Unwired)

| File | Intended URL | Status | Blocked By |
|------|--------------|--------|------------|
| `app/templates/pages/welcome.html` | `/` | ❌ Unused | main.py serves static |
| `app/templates/pages/onboarding-simple.html` | `/onboarding` | ❌ Unused | No route returns TemplateResponse |
| `app/templates/pages/tenant_home.html` | `/tenant/home` | ❌ Unused | Static file takes precedence |
| `app/templates/pages/tenant_dashboard.html` | `/tenant/dashboard` | ❌ Unused | No route wired |
| `app/templates/pages/vault.html` | `/tenant/vault` | ❌ Unused | Static vault.html exists |

**Issue:** Templates exist but no routes use `TemplateResponse()` to serve them

---

## ROUTER STATUS: 94 Routers, Most Disabled

### Core Routers (Actually Loaded in main.py)

| Router | Import Method | Status | Notes |
|--------|---------------|--------|-------|
| `health` | Direct import | ✅ Working | `/api/health` |
| `storage` | Direct import | ✅ Working | OAuth, reconnect, providers |
| `onboarding` | Direct import | ✅ Working | `/onboarding/start`, role selection |
| `plugins` | Direct import | ✅ Working | Plugin system |
| `development` | Direct import | ✅ Working | Dev tools |
| `documents` | `_safe_router_import` | ⚠️ Depends | May fail silently |
| `vault` | `_safe_router_import` | ❌ Disabled | Not mounted (see below) |
| `vault_engine` | `_safe_router_import` | ❌ Disabled | Not mounted |
| `timeline_unified` | `_safe_router_import` | ⚠️ Depends | Check if loaded |
| `briefcase` | `_safe_router_import` | ⚠️ Depends | Check if loaded |

### Routers With Import Errors (Broken)

| Router | Error | Fix Required |
|--------|-------|--------------|
| `vault_all_in_one` | `cannot import name 'get_current_user_id' from 'app.core.security'` | Add `get_current_user_id` to security.py OR change import |
| `advocate_invite` | `email-validator is not installed` | Run `pip install 'pydantic[email]'` |

### Routers NOT Loaded (Safe to Ignore for Now)

These are loaded via `_safe_router_import` but return `None` if they fail:

- `brain.py` - AI features (not tenant core)
- `copilot.py` - Assistant (not tenant core)
- `auto_mode.py` - Automation (not tenant core)
- `campaign.py` - Marketing (other division)
- `fraud_exposure.py` - Investigation (other division)
- `communication.py` - Multi-user (advocate feature)
- `document_delivery.py` - Multi-user (advocate feature)
- `court_forms.py` - Legal filing (legal role)
- `case_builder.py` - Legal prep (legal role)
- `analytics.py` - Tracking (not core)
- `research.py` - Research (not core)
- `mesh.py` - P2P (experimental)
- ...and 50+ more

**These don't hurt you** - they just don't load.

---

## THE WELCOME → ONBOARDING BREAK

### Current Flow (Broken)

```
User at: /static/public/welcome.html
         ↓
    Clicks: "Get Started" → calls enterApp('/onboarding/start')
         ↓
    Router: onboarding.py @ /onboarding/start
         ↓
    Logic: Check semptify_uid cookie
         ↓
    If NEW: redirect to /onboarding/select-role.html
         ↓
    PROBLEM: Static file served directly, no Jinja2 context
         ↓
    Result: Page loads but can't access SSOT navigation API
         ↓
    User clicks role → static JS tries to navigate
         ↓
    Navigation fails or goes to wrong place
```

### What Should Happen (Fixed)

```
User at: / (router serves TemplateResponse with welcome.html)
         ↓
    Clicks: "Get Started" → fetch('/onboarding/start')
         ↓
    Router: onboarding.py @ /onboarding/start
         ↓
    Logic: Check semptify_uid cookie
         ↓
    If NEW: redirect to /onboarding/select-role
         ↓
    Route: Returns TemplateResponse with onboarding-simple.html + SSOT context
         ↓
    Template: Uses {{ navigation.role_select_path }} etc.
         ↓
    User selects tenant role → POST to /onboarding/role
         ↓
    Redirect: /onboarding/storage
         ↓
    Route: Returns TemplateResponse with storage-select.html
         ↓
    User picks Google Drive → OAuth flow
         ↓
    Callback: /storage/oauth/callback
         ↓
    Success: redirect to /tenant/home
         ↓
    Route: Returns TemplateResponse with tenant_home.html
```

---

## RECONNECT FLOW STATUS

### According to BUILD_GUIDE_SSOT.md (April 29)

**Claimed:** "Reconnect Flow VERIFIED ✅"

**Tested:**
- ✅ Valid session → home (no OAuth)
- ✅ Invalid session → silent OAuth → home
- ✅ Return to task with `?return_to=`

**But:** Welcome page integration NOT tested

### Actual Problem

The welcome page has TWO CTAs:
1. "Get Started" → `/onboarding/start` (for new users)
2. **Missing:** "Returning User?" → `/storage/reconnect` (for existing users)

**Current:** One button tries to do both - detects via cookie
**Issue:** Cookie detection logic may be failing

---

## DETOUR PLAN (While Fixing)

Don't delete these - just bypass them:

### Routes to Detour Around (Keep Files, Disable in main.py)

```python
# In main.py, comment these out or set to None:

# NON-CORE (Other Divisions)
campaign_router = None  # Marketing/public exposure
fraud_exposure_router = None  # Investigation
public_exposure_router = None  # Bad actor reporting

# NON-CORE (Advocate/Legal Roles - Future)
advocate_router = None
legal_router = None  
manager_router = None
communication_router = None
document_delivery_router = None
invite_codes_router = None

# NON-CORE (AI/Brain - Heavy)
brain_router = None
copilot_router = None
auto_mode_router = None
emotion_router = None

# NON-CORE (Court - Legal Role)
court_forms_router = None
court_packet_router = None
eviction_defense_router = None
case_builder_router = None

# NON-CORE (Analytics/Research)
analytics_router = None
research_router = None
crawler_router = None

# BROKEN (Fix Later)
vault_all_in_one_router = None  # Import error
advocate_invite_router = None  # Missing dependency
```

### Routes to Keep (Tenant Core)

```python
# KEEP THESE - Tenant Minimum Viable
health_router ✅           # System status
storage_router ✅          # OAuth, reconnect, providers
onboarding_router ✅        # Welcome, role select, storage
plugins_router ✅          # Extensions
development_router ✅      # Dev tools (you)

# VERIFY THESE LOAD
documents_router ⚠️         # Document upload/view
timeline_unified_router ⚠️ # Timeline display
briefcase_router ⚠️        # Document viewer (vault view)
vault_router ❌           # Currently disabled - needs fix
```

---

## IMMEDIATE FIXES NEEDED

### Fix 1: Welcome Page Router (30 min)

**File:** `app/main.py` or `app/routers/onboarding.py`

**Add:**
```python
@router.get("/")
async def welcome_page(request: Request):
    """Serve welcome page via Jinja2 with SSOT context."""
    return templates.TemplateResponse(
        "pages/welcome.html",
        {
            "request": request,
            "navigation": navigation.to_dict(),
            "entry_point": "/onboarding/start"
        }
    )
```

**Remove:** Static file serving for `/` (or deprioritize)

### Fix 2: Vault Router Import (15 min)

**File:** `app/core/security.py`

**Check if exists:** `get_user_id` (line 30 in vault_all_in_one imports this)

**If missing, add:**
```python
def get_current_user_id(request: Request) -> Optional[str]:
    """Extract user ID from request cookies."""
    from app.core.user_id import parse_user_id, COOKIE_USER_ID
    cookie = request.cookies.get(COOKIE_USER_ID)
    if not cookie:
        return None
    user_id, _, _ = parse_user_id(cookie)
    return user_id
```

**Then in vault_all_in_one.py line 30:**
```python
# Change FROM:
from app.core.security import get_user_id

# Change TO:
from app.core.security import get_current_user_id as get_user_id
```

### Fix 3: Template Wiring (1 hour)

**Create:** `app/routers/tenant.py` (or add to existing)

```python
@router.get("/tenant/home")
async def tenant_home(request: Request, user_id: str = Depends(get_current_user_id)):
    """Tenant home/dashboard - requires auth."""
    if not user_id:
        return RedirectResponse(url="/onboarding/start")
    
    return templates.TemplateResponse(
        "pages/tenant_home.html",
        {
            "request": request,
            "user_id": user_id,
            "navigation": navigation.to_dict(),
            # Add stats, documents count, etc. from DB
        }
    )

@router.get("/tenant/vault")
async def tenant_vault(request: Request, user_id: str = Depends(get_current_user_id)):
    """Tenant vault view."""
    if not user_id:
        return RedirectResponse(url="/onboarding/start")
    
    return templates.TemplateResponse(
        "pages/vault.html",
        {
            "request": request,
            "user_id": user_id,
            "navigation": navigation.to_dict(),
        }
    )
```

---

## FILE LEGEND (What's What)

### Jinja2 Templates (30 files - Use These)

Location: `app/templates/pages/`

| File | Purpose | Status |
|------|---------|--------|
| `welcome.html` | Landing page | Needs route to serve it |
| `onboarding-simple.html` | Role + storage selection | Needs route |
| `tenant_home.html` | Post-login dashboard | Needs route |
| `tenant_dashboard.html` | Full dashboard | Needs route |
| `vault.html` | Document vault | Needs route |
| `timeline.html` | Timeline view | Needs route |
| `register.html` | User registration | Needs integration |

### Static Files (100+ files - Deprecating)

Location: `static/`

| Folder | Contents | Action |
|--------|----------|--------|
| `static/public/` | welcome, about, privacy | Keep as fallback |
| `static/onboarding/` | select-role, storage-select | **Deprecate** - move to Jinja2 |
| `static/tenant/` | dashboard, vault | **Deprecate** - use Jinja2 |
| `static/advocate/` | advocate UI | Ignore for now |
| `static/legal/` | legal UI | Ignore for now |
| `static/manager/` | manager UI | Ignore for now |
| `static/admin/` | admin UI | Ignore for now |

---

## SUCCESS CRITERIA (Working Tenant Flow)

**Test these in order:**

1. ✅ Visit `/` → See Jinja2 welcome page (not static)
2. ✅ Click "Get Started" → Go to `/onboarding/start`
3. ✅ New user → See Jinja2 role selection
4. ✅ Select "Tenant" → Go to `/onboarding/storage`
5. ✅ Pick storage provider → OAuth flow
6. ✅ OAuth success → Redirect to `/tenant/home`
7. ✅ See Jinja2 tenant home with real data
8. ✅ Click "Vault" → See Jinja2 vault with upload working
9. ✅ Upload document → Success, appears in vault
10. ✅ Log out, clear cookies
11. ✅ Visit `/` again → Click "Get Started"
12. ✅ Returning user → Seamless reconnect (no OAuth popup if session valid)

**When all 12 pass → Tenant core is working.**

---

## NEXT STEPS

Pick ONE:

1. **Fix Import Error First** (15 min) - Unblock vault_all_in_one
2. **Wire Welcome Page** (30 min) - Start Jinja2 serving
3. **Create Detour List** (30 min) - Comment out non-core in main.py
4. **Test Current State** (1 hour) - Document what's actually broken

**Which do you want to do first?**
