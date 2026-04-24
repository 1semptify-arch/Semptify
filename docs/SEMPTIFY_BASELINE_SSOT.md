# Semptify 5.0 - Master Baseline SSOT

**Status**: Single Source of Truth for ALL Semptify Development  
**Created**: 2026-04-23  
**Rule**: This document is the MASTER. Update it before/during/after any work.

---

## 🎯 PROJECT BASELINE - CURRENT STATE

### Core Principle
**One source of truth, one place to check, one place to update.**

---

## 📊 SYSTEM STATUS OVERVIEW

| Domain | Status | SSOT Location |
|--------|--------|---------------|
| **Backend Architecture** | ✅ Stable | `app/` - Modular, SSOT hardened |
| **Database Schema** | ✅ Stable | Alembic migrations + SSOT contracts |
| **ID Generation** | ✅ Complete | `app/core/id_gen.py` - 37 prefixes |
| **File Storage** | ✅ Complete | Cloud-first, stateless |
| **Frontend Entry** | ✅ Complete | `static/public/welcome.html` |
| **Onboarding Flow** | 🔄 In Progress | `static/onboarding/` - Mechanic done, design pending |
| **OAuth/Storage** | ✅ Complete | Working, reconnect flow needs UI |
| **Vault System** | ✅ Complete | Unified overlay manager |
| **Timeline** | ✅ Complete | Interactive timeline component |
| **Rehome** | ✅ Complete | Generated in user cloud, for device recovery |
| **Returning User** | ⏳ Not Started | Needs contract + implementation |

---

## 📁 FOLDER STRUCTURE (SSOT)

### Active Development (`static/` - Work Here)

```
static/
├── public/                      # Public pages (no auth required)
│   ├── welcome.html            # ⭐ ENTRY POINT - Two buttons: New/Returning
│   ├── about.html              # About Semptify
│   ├── privacy.html            # Privacy policy
│   └── terms.html              # Terms of service
│
├── reconnect/                   # ⭐ RETURNING USER (separate from onboarding!)
│   └── index.html              # Reconnect UI for existing users
│                               # SEPARATE SYSTEM - do not mix with onboarding
│
├── onboarding/                 # ⭐ NEW USER ONBOARDING (complete, don't touch)
│   ├── select-role.html        # Step 1: Role selection (3 roles)
│   └── validation/             # Role validation (pending)
│       ├── validate-advocate.html  ⏳
│       └── validate-legal.html     ⏳
│
├── tenant/                      # Tenant dashboard (post-auth) 🔄 Legacy Audit Needed
├── advocate/                    # Advocate dashboard (post-auth) 🔄 Legacy Audit Needed
├── legal/                       # Legal dashboard (post-auth) 🔄 Legacy Audit Needed
├── manager/                     # Manager dashboard (post-auth) 🔄 Legacy Audit Needed
├── admin/                       # Admin panel (post-auth) 🔄 Legacy Audit Needed
│
├── components/                  # Reusable UI components
├── shared/                      # Shared resources
├── templates/                   # Jinja2 templates
├── css/                         # Stylesheets
├── js/                          # JavaScript modules
├── assets/                      # Images, icons, fonts
├── docs/                        # Static help docs
├── tools/                       # Utility tools
└── office/                      # Office management
```

### Reference Only (`staticbac/` - DO NOT EDIT)

```
staticbac/
└── onboarding/                  # Old reference files
    ├── welcome.html            # Backup reference
    └── select-role.html        # Backup reference
```

---

## 🛣️ ROUTE MAP (SSOT)

| URL | File/Handler | Auth | Status | Notes |
|-----|--------------|------|--------|-------|
| `/` | `static/public/welcome.html` | No | ✅ Active | ⭐ SINGLE ENTRY POINT - Smart Gate checkpoint |
| `/storage/reconnect` | `static/reconnect/index.html` | No | ✅ Active | ⭐ SEPARATE: Returning user reconnect |
| `/onboarding/select-role.html` | `static/onboarding/select-role.html` | No | ✅ Active | ⭐ SEPARATE: New user onboarding Step 1 |
| `/onboarding/validation/validate-advocate.html` | (pending) | No | ⏳ Pending | Invite code validation |
| `/onboarding/validation/validate-legal.html` | (pending) | No | ⏳ Pending | Bar verification |
| `/storage/providers` | API endpoint | No | ✅ Active | OAuth provider selection |
| `/rehome/{user_id}` | `storage.py` endpoint | No | ✅ Active | Device recovery (from Rehome.html in cloud) |
| `/tenant/*` | `static/tenant/` | Yes | 🔄 Legacy | Needs audit/consolidation |
| `/advocate/*` | `static/advocate/` | Yes | 🔄 Legacy | Needs audit/consolidation |
| `/legal/*` | `static/legal/` | Yes | 🔄 Legacy | Needs audit/consolidation |
| `/manager/*` | `static/manager/` | Yes | 🔄 Legacy | Needs audit/consolidation |
| `/admin/*` | `static/admin/` | Yes | 🔄 Legacy | Needs audit/consolidation |

**Legend**: ✅ Complete | 🔄 Legacy/Needs Work | ⏳ Pending

---

## 🚫 NO ACCOUNTS - Storage-Based Identity

**CRITICAL ARCHITECTURE RULE**: Semptify has NO user accounts of any kind.

**What This Means**:
- ❌ No email registration
- ❌ No passwords  
- ❌ No "accounts" to create or manage
- ❌ No personal information tracked or stored by Semptify
- ✅ Your identity = Your connected storage
- ✅ Your data = Stored only in your cloud storage (Google Drive, Dropbox, OneDrive)
- ✅ Your control = You own and manage everything

**How It Works**:
1. User connects their existing cloud storage
2. Semptify generates a temporary identifier: `GU7x9kM2pQ` (provider + role + random)
3. Identifier stored in cookie only - no server-side account
4. All documents, data, everything lives in user's storage
5. Semptify never sees or stores personal information

**Reconnect Flow**:
- Returning users click their storage provider
- OAuth verifies their provider identity
- System restores their session
- No "account lookup" - just storage reconnection

**SSOT**: `app/core/user_id.py`  
**Status**: ✅ Enforced  
**Rule**: Never implement account-based features. Never track personal data.

---

## � SMART GATE CHECKPOINT (Single Entry Point)

**SSOT**: `app/core/checkpoint_middleware.py`  
**Status**: ✅ Active  
**Purpose**: Mandatory welcome page checkpoint for new users

**Logic:**
```
User Request → Check:
  ├─ Has session (semptify_uid)? → ✅ ALLOW (returning)
  ├─ Has checkpoint cookie? → ✅ ALLOW (saw welcome)
  ├─ Protected path + no credentials? → 🚪 Redirect to welcome
  └─ Public path → ✅ ALLOW
```

**Cookies:**
- `semptify_checkpoint=acknowledged` - Set when user clicks button on welcome page
- `semptify_uid` - User session (bypasses checkpoint)

**Protected Paths** (require checkpoint if no session):
- `/tenant/*`, `/advocate/*`, `/legal/*`, `/manager/*`, `/admin/*`
- `/vault/*`, `/documents/*`, `/timeline/*`, `/case/*`, `/home`

**Exempt Paths** (always allow):
- `/`, `/static/*`, `/public/*`, `/onboarding/*` (during setup)
- `/storage/reconnect`, `/storage/providers`, `/storage/callback`
- `/api/user/lookup`, `/api/session/restore`

**Legal Purpose**: Validates Semptify's right to work with user documents. User must actively click through welcome page (acknowledging Terms/Privacy) before accessing protected routes.

---

## ✅ COMPLETED SYSTEMS (Do Not Touch Unless Bug Fix)

### 1. ID Generation System
- **SSOT**: `app/core/id_gen.py`
- **Status**: ✅ Complete
- **Format**: `{prefix}_{16-char alphanumeric}`
- **Prefixes**: 37 defined (doc, evt, cal, con, inv, job, anl, aud, req, msg, sigreq, sig, att, del, ext, hlt, ann, ovl, plan, camp, wiz, conv, frd, prs, chk, fx, not, pack, batch, item, collab, ask, node, upd, trn, evid, act, cout, def, mot, cmp)

### 2. Unified Overlay System
- **SSOT**: `app/services/unified_overlay_manager.py`
- **Status**: ✅ Complete
- **Purpose**: Cloud-only overlay storage, stateless

### 3. Vault Storage System
- **SSOT**: `app/services/storage/vault_manager.py`
- **Status**: ✅ Complete
- **Structure**: `Semptify5.0/Vault/documents/`, `.overlay/`, `timeline/`
- **Includes**: Rehome.html generation in user cloud

### 4. Timeline System
- **SSOT**: `app/routers/timeline_unified.py`, `app/services/timeline_chronology.py`
- **Status**: ✅ Complete
- **Features**: Interactive timeline, date axis switching, search, facets

### 5. Performance Monitoring
- **SSOT**: `app/core/performance_monitor.py`
- **Status**: ✅ Complete

### 6. Database Layer
- **SSOT**: `app/core/database_pool.py`, Alembic migrations
- **Status**: ✅ Complete
- **Features**: Connection pooling, query optimization, caching

### 7. Rate Limiting
- **SSOT**: `app/core/advanced_rate_limiter.py`
- **Status**: ✅ Complete

### 8. OAuth/Storage Backend
- **SSOT**: `app/routers/storage.py`, `app/services/storage/`
- **Status**: ✅ Complete
- **Providers**: Google Drive, Dropbox, OneDrive

---

## 🔄 IN PROGRESS / NEEDS WORK

### 1. Onboarding Flow - MECHANICS DONE, DESIGN PENDING
**Current State**:
- ✅ Welcome page with two buttons (New/Returning)
- ✅ Role selection page (3 roles)
- ⏳ Validation pages (Advocate invite, Legal bar verification)
- ⏳ Storage provider selection UI
- ⏳ Returning user reconnect flow

**Next Actions**:
- Create validation pages
- Create storage provider selection page
- Implement returning user reconnect flow

### 2. Frontend Page Consolidation
**Current State**: 105 HTML files, many duplicates
**From PAGE_INVENTORY.md**:
- 6 entry points (needs 1)
- 4 dashboard versions (needs 1)
- 6 document management versions (needs 1)
- 5 timeline versions (needs 1-2)
- 2 calendar versions (needs 1)

**Next Actions**:
- Audit legacy role folders (tenant/, advocate/, legal/, manager/, admin/)
- Consolidate to single dashboard
- Archive duplicates

### 3. WebSocket/Real-time Notifications
**Status**: 50% complete
**Next Actions**:
- Create WebSocket router
- Implement notification system

---

## ⏳ PENDING TASKS (Priority Order)

### High Priority
1. **Returning User Reconnect Flow**
   - Contract for returning user process
   - UI page for reconnect
   - Route: `/storage/reconnect`

2. **Role Validation Pages**
   - Advocate: Invite code input
   - Legal: Bar number verification
   - Files: `validation/validate-advocate.html`, `validate-legal.html`

3. **Storage Provider Selection**
   - UI for picking Google/Dropbox/OneDrive
   - Triggered after role selection

### Medium Priority
4. **Dashboard Consolidation**
   - Audit all dashboard versions
   - Pick one (recommend dashboard-v2.html)
   - Archive others

5. **Document Pages Consolidation**
   - Merge 6 versions into 1

6. **Timeline Pages Consolidation**
   - Keep timeline.html + timeline-builder.html
   - Archive others

### Low Priority
7. **WebSocket Notifications**
8. **Advanced Search**
9. **Document Preview/Thumbnails**
10. **Batch Operations**
11. **Data Export/Import**

---

## 📝 WORKING LOG (Update This!)

### 2026-04-23 - Removed Email-Dependent Router
- ✅ Deleted `app/routers/advocate_invite.py` (required email-validator, violated NO ACCOUNTS architecture)
- ✅ Removed import from `app/main.py`
- ✅ Removed router registration from `app/main.py`
- ✅ Fixes startup error: "email-validator is not installed"

### 2026-04-23 - Footer Alignment Standard
- ✅ Center-aligned footer columns on all pages
- ✅ Updated `welcome.html` footer CSS
- ✅ Updated `reconnect/index.html` footer CSS
- ✅ Added Site-Wide Footer Standard to DESIGN SYSTEM section
- ✅ Documented required footer sections (Legal, Connect, Disclaimer, Bottom)

### 2026-04-23 - Baseline SSOT Created
- ✅ Created master baseline document
- ✅ Consolidated all status from various docs
- ✅ Verified current onboarding structure
- ✅ Documented completed vs pending work
- ✅ Established priority order for pending tasks

### 2026-04-22 - Frontend Onboarding Setup
- ✅ `welcome.html` in `static/public/welcome.html` (entry point)
- ✅ `select-role.html` in `static/onboarding/select-role.html`
- ✅ Root route serves from `static/public/`
- ✅ Onboarding router handles `/onboarding/*`
- ✅ Links: New User → `/onboarding/select-role.html`, Returning User → `/storage/reconnect`
- ✅ Updated `start-semptify.ps1` welcome URL
- ✅ Created `docs/FRONTEND_SSOT_GUIDE.md`

### 2026-04-22 - ID Generation & Timeline Complete
- ✅ ID generation refactor complete (34 files)
- ✅ Interactive timeline complete
- ✅ Data storage assessment complete

---

## 🎨 DESIGN SYSTEM (SSOT)

### Color Systems

**Onboarding/Public Pages (Light Blue Theme):**
```css
:root {
    --primary: #1e3a5f;           /* Deep blue - headers */
    --primary-light: #2d5a87;     /* Lighter blue - gradients */
    --accent: #3b82f6;            /* Bright blue - buttons/links */
    --warm: #f59e0b;              /* Amber - highlights */
    --text: #1e293b;              /* Dark text */
    --text-light: #475569;        /* Secondary text */
    --text-muted: #64748b;        /* Muted text */
    --bg: #fdfcfa;                /* Off-white background */
    --paper: #ffffff;             /* White cards */
    --border: #e2e8f0;            /* Light borders */
    --success: #10b981;           /* Green checkmarks */
}
```
Used by: `welcome.html`, `select-role.html`, `storage-select.html`, `reconnect/`

**Authenticated App UI (Dark Navy Theme):**
```css
:root {
    --color-bg-primary: #1a1a2e;      /* Dark navy background */
    --color-bg-secondary: #16213e;    /* Slightly lighter navy */
    --color-accent: #3b82f6;          /* Bright blue buttons/links */
    --color-text-primary: #ffffff;
    --color-text-secondary: #94a3b8;
    --color-border: rgba(255, 255, 255, 0.1);
}
```
Used by: Jinja2 templates (`base.html`), dashboards, logged-in pages

### Onboarding Template Structure
**Header and footer are IDENTICAL across all onboarding pages. Only `<article>` content changes.**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[Page] - Semptify</title>
    <style>
        /* Light Blue Theme for Onboarding */
        :root {
            --primary: #1e3a5f;
            --primary-light: #2d5a87;
            --accent: #3b82f6;
            --bg: #fdfcfa;
            --paper: #ffffff;
            --text: #1e293b;
        }
        
        body {
            background: var(--bg);
            color: var(--text);
        }
        
        .header {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
        }
    </style>
</head>
<body>
    <header class="header">...</header>
    <article class="article"><!-- PAGE-SPECIFIC CONTENT --></article>
    <footer class="footer">...</footer>
</body>
</html>
```

### Backend Role Names (MUST match exactly)
| Display Name | data-role value | Backend Code |
|--------------|-----------------|--------------|
| Tenant | `user` | U |
| Advocate | `advocate` | V |
| Legal | `legal` | L |
| Manager / Agency | `manager` | M |

### Typography
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
--text-sm: 0.875rem;
--text-base: 1rem;
--text-lg: 1.125rem;
--text-xl: 1.25rem;
--text-2xl: 1.5rem;
```

### Components
- Cards: `border-radius: 16px`, semi-transparent white background
- Buttons: `border-radius: 12px`, gradient or solid

### Site-Wide Footer Standard
**All Semptify pages MUST use center-aligned footer columns:**

```css
.footer-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1.5rem;
    max-width: 600px;
    margin: 0 auto 1rem;
    text-align: center;        /* CENTER alignment */
}

.footer-column h4 {
    text-align: center;        /* CENTER alignment */
}

.footer-column ul {
    text-align: center;        /* CENTER alignment */
    list-style: none;
}
```

**Required Footer Sections:**
- **Legal**: Privacy, Terms, Disclaimer
- **Connect**: Contact, Feedback
- **Disclaimer**: "Important: Semptify is an organizational tool, not legal advice..."
- **Bottom**: © 2024-2026 Semptify | Free Forever • No Ads • Open Source

---

## 🔧 DEVELOPMENT PROTOCOL

### Before Starting Work
1. Read this baseline document
2. Check if task is listed in Pending Tasks
3. Update Working Log with your intended changes
4. Verify SSOT files mentioned are current

### During Work
1. Update Working Log with progress
2. Update route map if adding/changing routes
3. Update folder structure if moving files
4. Mark tasks complete as you finish

### After Work
1. Verify all routes work
2. Test user flow end-to-end
3. Update this document with final status
4. Mark related tasks complete

---

## 🚀 QUICK START

### Run Server
```powershell
.\start-semptify.ps1
```

### Test Current Flow
1. `http://localhost:8000/` - Welcome with New/Returning buttons
2. Click "New User" → Role selection
3. Pick role → (next: storage selection - pending)

### Check SSOT
- Master baseline: `docs/SEMPTIFY_BASELINE_SSOT.md`
- Frontend specifics: `docs/FRONTEND_SSOT_GUIDE.md`
- Page inventory: `docs/PAGE_INVENTORY.md`

---

**END OF MASTER BASELINE - Keep Updated!**
