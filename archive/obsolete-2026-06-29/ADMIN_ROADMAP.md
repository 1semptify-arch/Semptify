# Semptify Admin System — Roadmap & Status

**Created**: 2026-06-08  
**Purpose**: Replace human recall with documented plan  
**Status**: Phase 1 (Functional Foundation)

---

## Executive Summary

The admin system is currently **fragmented** — you have:

- A stub admin module (`/admin-console/panel`) with only health check
- Rich static HTML pages (`/admin/`) that aren't wired to backend APIs
- A funding module with more admin functionality than the admin console
- No role-based access control on admin routes

This roadmap moves from "scattered stubs" to "functional admin hub" in 3 phases.

---

## Current State Audit

### What Exists

| Component | Location | Status | Issue |
| ----------- | ---------- | -------- | ------- |
| Admin Module Router | `app/modules/admin_console/router.py` | ⚠️ Stub | Only `/panel` and `/health` |
| Admin Panel UI | `app/modules/admin_console/ui/panel.html` | ⚠️ Minimal | Single health check button |
| Static Admin Dashboard | `static/admin/dashboard.html` | ✅ Rich UI | Not connected to module |
| Contract Browser | `static/admin/contract-browser.html` | ✅ Full-featured | Working, loads from `/api/workflow/module-contracts` |
| Function Browser | `static/admin/function-browser.html` | ✅ Full-featured | Needs audit |
| Page Editor | `static/admin/page-editor.html` | ✅ Exists | Needs audit |
| Review Checklist | `static/admin/review-checklist.html` | ✅ Exists | Needs audit |
| Funding Management | `app/modules/funding_mgmt/` | ✅ Functional | Has real CRUD, better than admin_console |

### What's Missing

| Capability | Priority | Notes |
| ------------ | ---------- | ------- |
| Role-based access control (ADMIN only) | **P0** | Currently no guard on `/admin/*` |
| Unified admin API | **P0** | Need endpoints for user management, system config |
| Connection between module and static pages | **P0** | `/admin` should serve the rich HTML |
| User management (list, view, impersonate) | **P1** | Support/debugging tool |
| System configuration UI | **P1** | Feature flags, tiers, gates |
| Audit log viewer | **P2** | Security/compliance |
| Analytics dashboard | **P2** | Real metrics, not stubs |

---

## Phase 1: Functional Foundation (Week 1) — IN PROGRESS

**Goal**: Admin routes are protected, unified dashboard loads, basic user management works.

### Tasks

#### 1.1 Admin Route Protection ✅ DONE

**Files**: `app/main.py`, `app/modules/admin_console/router.py`

- [x] Create `require_admin()` dependency guard (uses `require_role(UserRole.ADMIN)`)
- [x] Apply guard to all `/admin/*` routes (dashboard, contract-browser, function-browser, page-editor, review-checklist)
- [x] Apply guard to `/admin-console/*` API routes
- [ ] Test: Non-admin users get 403

#### 1.2 Unify Admin Entry Point ✅ DONE

**Files**: `app/modules/admin_console/router.py`, `app/main.py`

- [x] Change `/admin-console/panel` to redirect to `/admin/dashboard.html`
- [x] `/admin` redirects to `/admin/dashboard.html`
- [x] All admin pages protected by role check

#### 1.3 Create Admin API Foundation ✅ DONE

**Files**: `app/modules/admin_console/router.py`

- [x] `GET /admin-console/api/users` — List users (paginated)
- [x] `GET /admin-console/api/users/{user_id}` — User details
- [x] `POST /admin-console/api/users/{user_id}/impersonate` — Start impersonation session
- [x] `GET /admin-console/api/system/status` — System health + metrics
- [ ] `GET /admin/api/system/config` — Current configuration

#### 1.4 Wire Dashboard to APIs ✅ DONE

**Files**: `static/admin/dashboard.html`

- [x] Add user search widget with API integration (`/admin-console/api/users`)
- [x] Add user details view with impersonate button
- [x] Add system metrics auto-load (`/admin-console/api/system/status`)
- [x] Add Enter key support for search
- [ ] Add recent activity feed from logs (Phase 2)

### Phase 1 Definition of Done

- [x] `/admin` loads dashboard (protected)
- [x] Non-admin users cannot access `/admin/*` (403 Forbidden)
- [x] Can search/view users from admin panel (widget + API wired)
- [x] Can impersonate user for debugging (UI + API wired, token placeholder)

---

## Phase 2: Admin Capabilities (Week 2-3) — IN PROGRESS

**Goal**: Admin can manage users, configure system, view audit logs.

### Tasks

#### 2.1 User Management ✅ DONE

##### API Endpoints:

- [x] `GET /admin-console/api/users` — Real user list from session store (search, paginate)
- [x] `GET /admin-console/api/users/{id}` — User details with all sessions
- [x] `POST /admin-console/api/users/{id}/impersonate` — Full impersonation flow
- [x] `POST /admin-console/api/users/{id}/reset-gates` — Reset onboarding gates
- [x] `GET /admin-console/api/users/{id}/vault-summary` — Vault metadata for support
- [ ] Suspend/activate user accounts (needs account status table)
- [ ] Export user data (GDPR compliance) — pending data export service

#### 2.2 System Configuration 🔄 PENDING

- [ ] Toggle tiers (CORE, EXTENDED, ADMIN, etc.)
- [ ] Toggle modules on/off
- [ ] Configure feature flags
- [ ] Update navigation registry

#### 2.3 Audit & Compliance ✅ DONE

- [x] In-memory audit log with `_log_admin_action()` function
- [x] `GET /admin-console/api/audit` — View audit log with filters
- [x] `GET /admin-console/api/audit/actions` — List available action types
- [x] Auto-logged actions: impersonate, reset_gates, view_vault_summary
- [ ] Export audit logs — pending export service

#### 2.4 Content Management 🔄 PENDING

- [ ] Edit help articles
- [ ] Edit law library entries
- [ ] Manage letter templates

### Phase 2 Definition of Done

- [x] Can view active users and their sessions
- [x] Can impersonate users for debugging
- [x] Can reset user gates
- [x] Can view audit trail of admin actions
- [ ] Can enable/disable modules without deploy
- [ ] Can edit help content

---

## Phase 3: System Configuration & Content Management ✅ DONE

**Goal**: Configure system without deploy, manage help content.

### Tasks

#### 3.1 System Configuration ✅

- [x] `GET /admin-console/api/system/config` — Full config dump
- [x] `GET /admin-console/api/system/modules` — Module status with runtime state
- [x] `POST /admin-console/api/system/modules/{name}/toggle` — Enable/disable modules
- [x] `GET /admin-console/api/system/tiers` — Tier status
- [x] `POST /admin-console/api/system/tiers/{name}/toggle` — Enable/disable tiers
- [x] `GET /admin-console/api/system/feature-flags` — List feature flags
- [x] `POST /admin-console/api/system/feature-flags/{name}` — Set feature flag
- [x] `GET /admin-console/api/system/settings` — System settings
- [x] `POST /admin-console/api/system/settings/{name}` — Update setting
- [x] Dashboard: System Config card with live counts
- [x] Dashboard: Module Manager modal with enable/disable buttons

#### 3.2 Content Management ✅

- [x] `GET /admin-console/api/content/help-articles` — List help articles
- [x] `POST /admin-console/api/content/help-articles` — Create/update article
- [x] `DELETE /admin-console/api/content/help-articles/{id}` — Delete article
- [x] `GET /admin-console/api/content/law-library` — List law entries
- [x] `POST /admin-console/api/content/law-library` — Create/update entry
- [x] `GET /admin-console/api/content/letter-templates` — List templates
- [x] `POST /admin-console/api/content/letter-templates` — Create/update template

#### 3.3 Dashboard UI ✅

- [x] System Config card (shows tiers/modules/flags counts)
- [x] Module Manager button → opens modal with module list
- [x] Enable/Disable buttons per module with confirmation
- [x] Visual indicators (green=enabled, red=disabled)

### Phase 3 Definition of Done

- [x] Can enable/disable modules without deploy (runtime)
- [x] Can view all tiers and their status
- [x] Can toggle feature flags
- [x] Can manage help articles via API
- [x] Can manage law library entries via API
- [x] Can manage letter templates via API
- [x] Dashboard shows system config summary
- [x] Dashboard has module manager UI

---

## Phase 4: Advanced Admin 🚧 IN PROGRESS

**Goal**: Analytics, automation, remote management.

### Tasks

#### 4.1 Analytics Dashboard ✅

- [x] `GET /admin-console/api/analytics/overview` — High-level system overview
- [x] `GET /admin-console/api/analytics/signup-funnel` — Daily signup breakdown by role/provider
- [x] `GET /admin-console/api/analytics/feature-usage` — Feature usage metrics
- [x] `GET /admin-console/api/analytics/retention` — User retention (1d, 7d, 30d)
- [x] Dashboard: Analytics card with retention stats
- [x] Dashboard: Analytics details modal with full dashboard

#### 4.2 Automation 🚧 PENDING

- [ ] Scheduled tasks (cron UI)
- [ ] Batch operations
- [ ] Automated compliance checks

#### 4.3 Remote/CLI Admin 🚧 PENDING

- [ ] API key authentication for CLI
- [ ] Admin SDK (`semptify-admin` CLI)
- [ ] Remote vault inspection

---

## Immediate Next Actions (Tonight)

1. **Create admin route guard** (`require_admin()`)
2. **Redirect `/admin-console` to `/admin/dashboard.html`**
3. **Verify contract-browser works** (it has the API)
4. **Add user search to dashboard**

```python
## Quick win - add this to app/core/route_guards.py
async def require_admin(request: Request):
    user = await get_current_user(request)
    if user.role != UserRole.ADMIN:
        raise HTTPException(403, "Admin access required")
    return user
```

---

## Files to Know

| File | Purpose |
| ------ | --------- |
| `app/modules/admin_console/router.py` | Admin API routes (expand this) |
| `app/modules/admin_console/ui/panel.html` | Current stub panel |
| `static/admin/dashboard.html` | Rich admin dashboard (use this) |
| `static/admin/contract-browser.html` | Contract viewer (working) |
| `app/core/route_guards.py` | Add `require_admin()` here |
| `app/core/user_context.py` | Role definitions |
| `app/modules/funding_mgmt/router.py` | Reference for real admin functionality |

---

## Architecture Decision: Attached Role vs Separate App

**Decision**: Keep as Attached Role for now (simpler), migrate to Separate Admin App when:

- You have 3+ admin users
- You need audit compliance
- Admin features become complex (analytics, automation)

**Current approach**: Admin role in main app, `/admin/*` routes, ADMIN tier.

---

*Update this file after each session. Check off completed tasks.*
