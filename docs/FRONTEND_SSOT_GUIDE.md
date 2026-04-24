# Semptify 5.0 - Frontend SSOT Build-Out Guide

**STATUS**: Single Source of Truth for all frontend development  
**RULE**: Update this doc BEFORE/DURING any frontend changes  
**LAST UPDATED**: 2026-04-23

**RELATED DOCUMENTS**:
- 📋 **Master Baseline**: `docs/SEMPTIFY_BASELINE_SSOT.md` - System-wide status
- 📋 **Task Master**: `docs/TASK_MASTER.md` - Active task list with priorities
- 📋 **This Guide**: Frontend-specific structure and design

---

## SSOT Principle

This document is the **Single Source of Truth** for Semptify frontend:
- All folder structures documented here
- All page routes mapped here
- All design standards defined here
- All changes must be logged here

**Workflow**:
1. Check this doc before making changes
2. Update this doc when changing structure
3. Verify routes work after changes
4. Log all modifications in Working Log

---

## Folder Structure (SSOT)

```
static/                          # ACTIVE FRONTEND - All work here
├── public/                      # Public pages (no auth)
│   ├── welcome.html            # ⭐ Entry point (outside onboarding)
│   ├── about.html              # About Semptify
│   ├── privacy.html            # Privacy policy
│   └── terms.html              # Terms of service
│
├── onboarding/                # Onboarding flow
│   ├── select-role.html        # ⭐ Step 1: Role selection
│   └── validation/             # Role validation (pending)
│       ├── validate-advocate.html
│       └── validate-legal.html
│
├── tenant/                      # Tenant dashboard (post-auth)
├── advocate/                    # Advocate dashboard (post-auth)
├── legal/                       # Legal dashboard (post-auth)
├── manager/                     # Property manager (post-auth)
├── admin/                       # Admin panel (post-auth)
├── components/                  # Reusable UI components
├── shared/                      # Shared resources
├── templates/                   # Jinja2 templates
├── css/                         # Stylesheets
├── js/                          # JavaScript modules
├── assets/                      # Images, icons, fonts
├── docs/                        # Static documentation
├── tools/                       # Utility tools
└── office/                      # Office management

staticbac/                       # BACKUP ONLY - DO NOT EDIT
└── onboarding/                   # Reference files
```

---

## Route Mapping (SSOT)

| Route | File | Auth | Status |
|-------|------|------|--------|
| `/` | `static/public/welcome.html` | No | ✅ Active |
| `/onboarding/select-role.html` | `static/onboarding/select-role.html` | No | ✅ Active |
| `/storage/reconnect` | API endpoint | No | ✅ Active |
| `/storage/providers` | API endpoint | No | ✅ Active |
| `/tenant/` | `static/tenant/` | Yes | 🔄 Legacy |
| `/advocate/` | `static/advocate/` | Yes | 🔄 Legacy |
| `/legal/` | `static/legal/` | Yes | 🔄 Legacy |
| `/manager/` | `static/manager/` | Yes | 🔄 Legacy |
| `/admin/` | `static/admin/` | Yes | 🔄 Legacy |

**Legend**: ✅ Active | ⏳ Pending | 🔄 Legacy | ❌ Broken

---

## Design System (SSOT)

### Colors
- Primary: `#10b981` (emerald-500)
- Background: Linear gradient `#064e3b` → `#065f46`
- Text Primary: `#ffffff`
- Text Secondary: `#a7f3d0` (emerald-200)

### Typography
- Font: System font stack
- Headings: 1.5rem - 2rem
- Body: 0.9rem - 1rem

### Components
- Cards: `border-radius: 16px`, semi-transparent white
- Buttons: Gradient or solid, `border-radius: 12px`

---

## Working Log (SSOT)

### 2026-04-22 - Frontend Structure Setup
- ✅ `welcome.html` in `static/public/welcome.html` (entry point, outside onboarding)
- ✅ `select-role.html` in `static/onboarding/select-role.html` (step 1)
- ✅ Root route serves from `static/public/`
- ✅ Onboarding router handles `/onboarding/*` paths
- ✅ Links: New User → `/onboarding/select-role.html`, Returning User → `/storage/reconnect`
- ✅ Updated `start-semptify.ps1` welcome URL
- ✅ Created this SSOT guide

### 2026-04-23 - Baseline & Task Master Created
- ✅ Created `docs/SEMPTIFY_BASELINE_SSOT.md` - Master system status
- ✅ Created `docs/TASK_MASTER.md` - Prioritized task list
- ✅ Updated this guide with cross-references
- ✅ Established task priorities (High/Medium/Low)

### Next Tasks (See TASK_MASTER.md for full list)
- 🔴 **HIGH**: Task 1 - Returning User Reconnect Flow
- 🔴 **HIGH**: Task 2 - Advocate Validation Page  
- 🔴 **HIGH**: Task 3 - Legal Validation Page
- 🔴 **HIGH**: Task 4 - Storage Provider Selection Page
- 🟡 **MEDIUM**: Task 5-7 - Consolidate Dashboard/Document/Timeline pages
- 🟢 **LOW**: Task 8-10 - WebSocket, Search, Previews

---

## Change Protocol

1. **Before**: Read this guide, plan changes
2. **During**: Update Working Log in real-time
3. **After**: Test routes, verify SSOT is current

---

**Keep this document updated in real-time with all frontend changes**
