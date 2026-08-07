# Semptify HTML Template Inventory & Merger Analysis
**Generated:** May 22, 2026
**Scope:** Complete analysis of ALL HTML/Jinja2 templates including untracked, backup, and archive files

---

## Executive Summary

This analysis reveals **100+ HTML files** across the codebase with significant duplication and consolidation opportunities. The primary finding: **multiple parallel page ecosystems exist** that should be merged into a unified, SSOT-compliant template architecture.

### Key Findings (Updated with Untracked Files)

| Category | Count | Status |
|----------|-------|--------|
| **Total HTML Files** | **~110** | Analyzed |
| Jinja2 Templates (app/templates) | 25 | Active |
| Static HTML Files (static/) | 19 | Needs consolidation |
| **Backup/Archive (staticbac/)** | **50+** | **CANDIDATES FOR DELETION** |
| Design System Components | 15 | Reference only |
| Additional Template Systems | 8 | Modules, Dakota, etc. |
| **Total Duplication Sets** | **20+** | **Critical cleanup needed** |

### Critical Discovery: 4 Parallel Base Template Systems

1. `app/templates/base.html` - Main Jinja2 base (614 lines) ⭐ CANONICAL
2. `modules/core/templates/base.html` - Module base (83 lines)
3. `static/templates/base.html` - Static template base (166 lines)
4. `staticbac/` - 50+ legacy static files (ARCHIVE)

### Backup/Archive Files (staticbac/)

**This folder contains 50+ legacy HTML files including:**
- `briefcase.html` (108KB) - Massive legacy file
- `admin/gui_navigation_hub.html` (736 lines) - "Dead purple UI" per cleanup notes
- `command_center.html` (79KB) - Legacy dashboard
- `complaints.html` (88KB) - Legacy complaints system
- `badwelcome.html` (42KB) - Old welcome version
- `auto_mode_demo.html`, `batch_analysis_results.html` - Deleted per May 12 cleanup
- Multiple index.html versions across tenant/manager/legal/advocate folders

**Recommendation:** `staticbac/` is a backup folder - all files are candidates for deletion after verification.

---

## 1. File Inventory by Location

### 1.1 Jinja2 Templates (app/templates/pages/)

| File | Purpose | Lines | Route | Status |
|------|---------|-------|-------|--------|
| `welcome.html` | Process A - Role selection | 631 | `/` | **ACTIVE** |
| `tenant_home.html` | Tenant landing | 194 | `/tenant/home` | Active |
| `tenant_dashboard.html` | Full dashboard | 520 | `/tenant/dashboard` | Active |
| `tenant_journal.html` | Journal interface | 7,878 | `/tenant/journal` | Active |
| `tenant_inbox.html` | Communications | 8,960 | `/tenant/inbox` | Active |
| `tenant_capture.html` | Document capture | 10,889 | `/tenant/capture` | Active |
| `tenant_help.html` | Tenant help | 16,391 | `/tenant/help` | Active |
| `documents.html` | Document vault | 221 | `/documents` | Active |
| `vault.html` | Vault interface | 14,971 | `/vault` | Active |
| `library.html` | Library landing | 33 | `/library` | **MINIMAL** |
| `office.html` | Office hub | 46 | `/office` | **MINIMAL** |
| `tools.html` | Tools landing | 23 | `/tools` | **MINIMAL** |
| `help.html` | Help landing | 28 | `/help` | **MINIMAL** |
| `timeline.html` | Timeline view | 7,098 | `/timeline` | Active |
| `tenant.html` | Generic tenant | 2,612 | `/tenant` | **DEPRECATED?** |
| `legal.html` | Legal professional | 2,831 | `/legal` | Active |
| `advocate.html` | Advocate dashboard | 2,800 | `/advocate` | Active |
| `admin.html` | Admin panel | 2,861 | `/admin` | Active |
| `manager_dashboard.html` | Property manager | 10,268 | `/manager/dashboard` | Active |
| `semptify_hub.html` | Main hub | 13,669 | `/hub` | Active |
| `register.html` | Registration | 5,785 | `/register` | Active |
| `register_success.html` | Post-register | 2,221 | `/register/success` | Active |
| `auto_mode_panel.html` | Auto analysis | 12,708 | `/auto-mode` | Active |
| `auto_analysis_summary.html` | Analysis results | 9,679 | `/analysis-summary` | Active |
| `error.html` | Error page | 1,267 | Error handler | Active |

### 1.2 Static HTML Files (static/)

| File | Purpose | Lines | Duplicates Template? |
|------|---------|-------|---------------------|
| `welcome.html` | Static welcome | 646 | ✅ YES - `app/templates/pages/welcome.html` |
| `home.html` | Static home | 383 | ⚠️ PARTIAL - Similar to `tenant_home.html` |
| `library.html` | Static library | 536 | ✅ YES - `app/templates/pages/library.html` |
| `office.html` | Static office | 198 | ✅ YES - `app/templates/pages/office.html` |
| `tools.html` | Static tools | 19665 | ⚠️ EXTENSIVE - Needs review |
| `help.html` | Static help | 36034 | ⚠️ EXTENSIVE - Needs review |
| `search.html` | Search interface | 19019 | Unknown |

### 1.3 Static Subdirectories

| Directory | Files | Purpose |
|-----------|-------|---------|
| `static/onboarding/` | 6 files | Onboarding flow pages |
| `static/public/` | 8 files | Public marketing pages |
| `static/tenant/` | 7 files | Tenant-specific pages |
| `static/admin/` | 4 files | Admin interface |
| `static/advocate/` | 2 files | Advocate interface |
| `static/office/` | 4 files | Office sub-pages |
| `static/tools/` | 3 files | Tool interfaces |

### 1.4 Design System Components

| Directory | Count | Purpose |
|-----------|-------|---------|
| `design-system/components/function-groups/capture/` | 4 | Document capture |
| `design-system/components/function-groups/vault/` | 3 | Vault sidebar |
| `design-system/components/function-groups/understand/` | 3 | Analysis views |
| `design-system/components/function-groups/plan/` | 3 | Action planning |
| `design-system/components/function-groups/role-specific/` | 6 | Role dashboards |
| `design-system/components/function-groups/onboarding/` | 3 | Onboarding components |

### 1.5 Additional Template Systems

| Location | Files | Purpose |
|----------|-------|---------|
| `modules/core/templates/` | 3 | Module system base templates |
| `semptify_dakota_eviction/app/templates/` | 7+ | Dakota eviction module |
| `static/templates/` | 3 | Static page templates |
| `data/eviction_training/sample_templates/` | 3 | Training data (txt) |

### 1.6 Backup/Archive Files (staticbac/) ⚠️ UNTRACKED

**Status:** These are NOT tracked in git (in .gitignore or backup folder)

| File | Size | Purpose | Status |
|------|------|---------|--------|
| `briefcase.html` | 108,633 bytes | Legacy document system | **DELETE** |
| `command_center.html` | 79,263 bytes | Legacy dashboard | **DELETE** |
| `complaints.html` | 88,019 bytes | Legacy complaints | **DELETE** |
| `admin/gui_navigation_hub.html` | 736 lines | Dead purple UI | **DELETE** |
| `admin/documentation_hub.html` | unknown | Legacy docs | **DELETE** |
| `badwelcome.html` | 42,518 bytes | Old welcome | **DELETE** |
| `auto_mode_demo.html` | 18,571 bytes | Already deleted May 12 | **DELETE** |
| `batch_analysis_results.html` | 17,366 bytes | Already deleted May 12 | **DELETE** |
| `my_tenancy.html` | 10,935 bytes | Covered by tenant_home | **DELETE** |
| `auto_analysis_summary.html` | 18,812 bytes | Duplicate | **DELETE** |
| `dakota_defense.html` | 33,945 bytes | Legacy defense | **DELETE** |
| `vault.html` | 64,177 bytes | Duplicate of app version | **DELETE** |
| `law_library.html` | 54,005 bytes | Partial duplicate | **DELETE** |
| `legal_analysis.html` | 63,935 bytes | Duplicate | **DELETE** |
| `documents.html` | 684 bytes | Stub | **DELETE** |
| `page-index.html` | 54,988 bytes | Legacy page index | **DELETE** |
| `index.html` | 11,128 bytes | Multiple versions | **DELETE** |
| `home.html` | 21,840 bytes | Static version | **DELETE** |
| `help.html` | 38,534 bytes | Duplicate | **DELETE** |
| `calendar-v2.html`, `calendar.html` | 31K, 33K | Legacy calendars | **DELETE** |
| `storage_setup.html` | 45,500 bytes | Old onboarding | **DELETE** |
| `setup_wizard.html` | 65,377 bytes | Old wizard | **DELETE** |
| `module-converter.html` | 44,072 bytes | Legacy tool | **DELETE** |
| `page_editor.html` | 31,292 bytes | Legacy editor | **DELETE** |
| `mesh_network.html` | 23,328 bytes | Legacy network | **DELETE** |
| **Plus 25+ more files** | various | Legacy/duplicate | **REVIEW** |

### 1.7 Backup Files in static/

| File | Location | Purpose | Action |
|------|----------|---------|--------|
| `select-role.html.bak` | `static/onboarding/` | Old role select | **DELETE** |
| `storage-select.html.bak` | `static/onboarding/` | Old storage select | **DELETE** |

---

## 2. Consolidation Opportunities

### 2.1 HIGH PRIORITY: Welcome Page Triplication

**Issue:** 3 versions of the welcome page exist

| Version | Location | Lines | Style | Tech |
|---------|----------|-------|-------|------|
| **A** | `app/templates/pages/welcome.html` | 631 | Dark theme, CSS vars | Jinja2 |
| **B** | `static/welcome.html` | 646 | Light theme, serif font | Static |
| **C** | `static/public/welcome.html` | 702 | Light theme, SSOT features | Static |

**Recommendation:**
```
MERGE → Single canonical welcome.html
├── Use Version A (Jinja2) as base
├── Adopt Version B's content flow (article-style)
├── Adopt Version C's SSOT compliance features
└── Route: / (root) only
```

### 2.2 HIGH PRIORITY: Library Pages

| Version | Location | Lines | Features |
|---------|----------|-------|----------|
| **A** | `app/templates/pages/library.html` | 33 | Macro-based, minimal |
| **B** | `static/library.html` | 536 | Full-featured, state law API |
| **C** | `static/tenant/law-library.html` | 879 | Comprehensive law reference |

**Recommendation:**
```
MERGE → Single library ecosystem
├── Base: Version A (Jinja2 template)
├── Content: Merge Version B's resource cards + state law selector
├── Deep content: Link to Version C as /law-library
└── Routes: /library (hub) + /law-library (deep reference)
```

### 2.3 MEDIUM PRIORITY: Office Pages

| Version | Location | Lines | Approach |
|---------|----------|-------|----------|
| **A** | `app/templates/pages/office.html` | 46 | Macro-based, minimal |
| **B** | `static/office.html` | 198 | Full static, vault CTA |

**Recommendation:**
```
MERGE → Single office.html
├── Use Version A (Jinja2) as base
├── Add Version B's vault-cta component
├── Add "primary-actions" card grid
└── Route: /office
```

### 2.4 MEDIUM PRIORITY: Home/Dashboard Pages

| Version | Location | Lines | Purpose |
|---------|----------|-------|---------|
| **A** | `static/home.html` | 383 | Marketing + dashboard hybrid |
| **B** | `app/templates/pages/tenant_home.html` | 194 | Authenticated tenant home |
| **C** | `app/templates/pages/tenant_dashboard.html` | 520 | Full dashboard |
| **D** | `static/tenant/dashboard.html` | 21,395 | Comprehensive tenant dashboard |

**Recommendation:**
```
MERGE → Two-tier approach
├── /home → Marketing landing (Version A style)
├── /tenant/home → Authenticated home (merge B + C)
└── /tenant/dashboard → Full dashboard (Version D as reference)
```

### 2.5 LOW PRIORITY: Document/Vault Pages

| Version | Location | Lines |
|---------|----------|-------|
| **A** | `app/templates/pages/documents.html` | 221 |
| **B** | `app/templates/pages/vault.html` | 14,971 |
| **C** | `static/tenant/documents.html` | 17,887 |
| **D** | `staticbac/vault.html` | 64,177 | **DELETE** |

**Note:** Vault pages are complex; careful merge required.

### 2.6 CRITICAL: Base Template Consolidation

**Issue:** 4 different base.html templates exist:

| Version | Location | Lines | Theme | Purpose |
|---------|----------|-------|-------|---------|
| **A** | `app/templates/base.html` | 614 | Dark | ⭐ CANONICAL |
| **B** | `modules/core/templates/base.html` | 83 | Auto | Module system |
| **C** | `static/templates/base.html` | 166 | Ocean | Static pages |
| **D** | `staticbac/` (implied) | varies | Various | Legacy |

**Recommendation:**
```
MERGE → Single base.html
├── Use Version A (app/templates/base.html) as canonical
├── Add conditional logic for light/dark theme
├── Modules should extend canonical base
└── Delete Version B and C after migration
```

### 2.7 UNTRACKED FILES: staticbac/ Cleanup

**Total Files in staticbac/:** 50+ HTML files
**Status:** Not tracked in git
**Action:** Bulk deletion after verification

**Key Files to Delete:**
- All `admin/*hub*.html` files (dead purple UI)
- `briefcase.html` (108KB legacy)
- `command_center.html` (79KB legacy)
- All calendar variants (legacy)
- `badwelcome.html` (old version)
- Duplicate index.html files

---

## 3. Visual Design Analysis

### 3.1 Color Systems

| Theme | Primary | Secondary | Accent | Background |
|-------|---------|-----------|--------|------------|
| **Dark (Jinja2)** | `#1a1a2e` | `#16213e` | `#3b82f6` | Gradient dark |
| **Light (Static)** | `#1a237e` | `#283593` | `#3949ab` | `#ffffff` |
| **Warm (Welcome)** | `#1e3a5f` | `#2d5a87` | `#3b82f6` | `#fdfcfa` |
| **Purple (Tenant)** | `#4c1d95` | `#5b21b6` | `#7c3aed` | `#faf8ff` |

**Recommendation:** Standardize on 2 themes:
1. **Dark Theme**: For authenticated app (tenant, advocate, legal)
2. **Light Theme**: For public/marketing pages

### 3.2 Typography

| Source | Font Family | Use Case |
|--------|-------------|----------|
| Jinja2 templates | `Inter`, system-ui | Modern app UI |
| Static welcome | `Georgia`, serif | Editorial content |
| Law library | `-apple-system`, sans | Content-heavy |

**Recommendation:** Use `Inter` for all authenticated pages; serif only for long-form content.

### 3.3 Layout Patterns

| Pattern | Used In | Lines of CSS |
|---------|---------|--------------|
| Card grid (3-col) | Library, Office | ~20 lines |
| Hero + content | Most pages | ~30 lines |
| Sidebar layout | Dashboard, Vault | ~100 lines |
| Full-width article | Welcome static | ~50 lines |

---

## 4. Route Structure Analysis

### 4.1 Current Route Conflicts

```
CONFLICTS DETECTED:
├── /welcome.html → static/welcome.html
├── /           → app/templates/pages/welcome.html (Jinja2)
├── /home     → static/home.html (if exists)
├── /home     → router → tenant_home.html
├── /library  → static/library.html
├── /library  → router → library.html (Jinja2)
├── /office   → static/office.html
└── /office   → router → office.html (Jinja2)
```

**Issue:** Static files shadow Jinja2 routes in some configurations.

### 4.2 SSOT Navigation Registry

Per `app/core/navigation.py`, canonical paths are:

```python
MAIN_NAV = [
    "/home",  # → tenant_home.html
    "/library",  # → library.html
    "/office",  # → office.html
    "/tools",  # → tools.html
    "/help",  # → help.html
]

ONBOARDING_FLOW = [
    "/",  # → welcome.html
    "/onboarding/select-role.html",
    "/onboarding/providers",
    "/storage/providers",  # Reconnect entry
    "/onboarding/vault-setup",
    "/onboarding/complete",  # → dashboard
]
```

---

## 5. Proposed Consolidation Plan

### Phase 1: Merge Duplicate Welcome Pages

**Action:** Delete `static/welcome.html` and `static/public/welcome.html`
**Keep:** `app/templates/pages/welcome.html` as canonical
**Update:** Add SSOT features from public version

### Phase 2: Merge Library Pages

**Action:**
1. Keep `app/templates/pages/library.html` as hub
2. Move `static/library.html` content to API-driven components
3. Keep `static/tenant/law-library.html` as deep reference at `/law-library`

### Phase 3: Standardize on Jinja2 Templates

**Action:** For each static HTML file with Jinja2 equivalent:
1. Compare functionality
2. Migrate unique features to Jinja2 version
3. Delete static version
4. Update routes

### Phase 4: Design System Unification

**Action:**
1. Move all CSS to `design-system/`
2. Create theme variables for dark/light
3. Update all templates to use design system classes

---

## 6. File Dependency Map

### 6.1 Template Inheritance

```
base.html
├── welcome.html
├── library.html
├── office.html
├── tools.html
├── help.html
├── documents.html
├── vault.html (standalone, no extends)
├── tenant_dashboard.html (standalone)
└── [role pages].html
```

### 6.2 Component Includes

```
documents.html
└── components/upload_zone.html

design-system/
├── components/function-groups/
│   ├── capture/
│   │   ├── upload-zone.html
│   │   ├── voice-intake.html
│   │   └── quick-input.html
│   ├── vault/
│   │   ├── vault-sidebar.html
│   │   └── vault-sidebar-clean.html
│   ├── understand/
│   │   ├── timeline-view.html
│   │   ├── risk-detection.html
│   │   └── rights-analysis.html
│   └── role-specific/
│       ├── tenant/
│       │   ├── dashboard.html
│       │   ├── emergency-actions.html
│       │   └── case-summary.html
│       ├── advocate/
│       │   └── dashboard.html
│       └── legal/
│           └── dashboard.html
```

---

## 7. Routes and Functions Matrix

| Page | Route | Main Function | API Endpoints Used |
|------|-------|---------------|-------------------|
| Welcome | `/` | Role selection, entry | `/api/workflow/route` |
| Home | `/home` | Dashboard hub | `/api/components/config/tenant` |
| Library | `/library` | Resource hub | `/api/states/` |
| Law Library | `/law-library` | Deep reference | Static content |
| Office | `/office` | Case management | Various |
| Documents | `/documents` | Vault access | `/api/vault/upload` |
| Timeline | `/timeline` | Event journal | `/api/timeline/` |
| Tools | `/tools` | Calculators, generators | Tool-specific |
| Help | `/help` | Support resources | Static + `/api/help` |

---

## 8. Recommended Final Structure

### After Consolidation (Target State)

```
app/templates/
├── base.html                    (canonical base - merged from 4 versions)
├── pages/
│   ├── welcome.html             (merged from 3 versions)
│   ├── home.html                (marketing landing)
│   ├── library.html             (resource hub - merged)
│   ├── law_library.html         (deep law reference)
│   ├── office.html              (case management - merged)
│   ├── tools.html               (tool hub)
│   ├── help.html                (support)
│   ├── documents.html           (vault interface)
│   ├── timeline.html            (journal)
│   ├── tenant/
│   │   ├── home.html            (authenticated)
│   │   ├── dashboard.html       (full dashboard)
│   │   ├── journal.html         (journal view)
│   │   └── inbox.html           (communications)
│   ├── advocate/
│   │   └── dashboard.html
│   ├── legal/
│   │   └── dashboard.html
│   └── admin/
│       └── dashboard.html
└── components/
    ├── ui_macros.html           (shared macros)
    ├── upload_zone.html
    ├── document_card.html
    └── functions_bar.html

static/                          (minimal - only what's needed)
├── public/                      (marketing pages only)
│   ├── about.html
│   ├── contact.html
│   ├── privacy.html
│   ├── terms.html
│   └── disclaimer.html
├── onboarding/                  (if not moved to templates)
│   └── [onboarding pages]
└── js/
    └── core/
        ├── vault-portal.js
        └── unified-footer-loader.js

design-system/                   (all styling)
├── tokens/
│   ├── colors.css
│   ├── typography.css
│   └── spacing.css
├── components/
│   ├── buttons.css
│   ├── cards.css
│   └── forms.css
└── patterns/
    └── [layout patterns]

modules/
├── core/
│   └── templates/               (DELETE - use app/templates/base.html)
└── [other modules]

# DELETED:
# - staticbac/ (entire folder - 50+ legacy files)
# - static/templates/ (duplicate base.html)
# - static/*.html duplicates of app/templates
# - *.bak files
```

### Cleanup Commands (Reference)

```bash
# Remove backup folder (after verification)
rm -rf staticbac/

# Remove .bak files
find static/ -name "*.bak" -delete

# Remove duplicate static HTML files (already have Jinja2 versions)
# Compare and migrate unique features first
rm static/welcome.html
rm static/library.html
rm static/office.html
```

---

## 9. Implementation Priority (Updated with Untracked Files)

| Priority | Action | Effort | Impact |
|----------|--------|--------|--------|
| 🔴 **Critical** | **Delete staticbac/ folder** (50+ legacy files) | 1h | **HIGH - 5MB+ cleanup** |
| 🔴 **Critical** | Delete .bak files in static/ | 15min | Low - Cleanup |
| 🔴 **Critical** | Delete duplicate static welcome pages | 1h | High - Removes confusion |
| 🔴 **Critical** | Consolidate library pages | 4h | High - Single entry point |
| 🟡 **High** | Merge 4 base.html templates into 1 | 3h | High - Architecture |
| 🟡 **High** | Merge office pages | 2h | Medium - Consistent UX |
| 🟡 **High** | Standardize home/dashboard | 4h | Medium - Clear hierarchy |
| 🟢 **Medium** | Migrate tools/help to Jinja2 | 3h | Low - Maintainability |
| 🟢 **Medium** | Design system CSS consolidation | 8h | Medium - Technical debt |
| ⚪ **Low** | Clean up design system duplicates | 4h | Low - Organization |

### Quick Cleanup Script

```bash
#!/bin/bash
# quick-cleanup.sh - Run after verification

echo "Removing backup files..."
rm -rf staticbac/
find static/ -name "*.bak" -delete

echo "Removing duplicate static HTML files..."
# These have Jinja2 equivalents in app/templates/pages/
rm -f static/welcome.html
rm -f static/library.html
rm -f static/office.html
rm -f static/home.html

echo "Cleanup complete. Run git status to verify."
```

### Size Impact

| Action | Files | Size Saved |
|--------|-------|------------|
| Delete staticbac/ | ~50 files | ~5MB |
| Delete .bak files | 2 files | ~50KB |
| Remove static duplicates | 4 files | ~200KB |
| **Total** | **~56 files** | **~5.3MB** |

---

## 10. Verification Checklist

After consolidation:

### Cleanup Verification
- [ ] `staticbac/` folder deleted
- [ ] All `.bak` files removed
- [ ] Duplicate static HTML files removed (those with Jinja2 equivalents)
- [ ] No orphaned files (not referenced by any route)

### Architecture Verification
- [ ] Single `base.html` (all others deleted/merged)
- [ ] All pages serve from Jinja2 templates (not static)
- [ ] No duplicate content across static/template boundaries
- [ ] SSOT navigation registry matches actual routes
- [ ] All pages use unified-footer-loader.js
- [ ] Dark theme for authenticated pages
- [ ] Light theme for public pages
- [ ] `python tests/test_ssot_architecture.py` passes
- [ ] No hardcoded URLs (all from `navigation` registry)
- [ ] All routes documented in navigation.py

### Git Verification
- [ ] `git status` shows only expected changes
- [ ] No untracked HTML files remaining (except in static/public/)
- [ ] `.gitignore` updated if needed
- [ ] Commit message documents cleanup scope

---

## Appendix: Complete File Count Summary

### By Location

| Location | Count | Tracked | Action |
|----------|-------|---------|--------|
| `app/templates/` | 25 | ✅ Yes | Keep |
| `static/` (root) | 6 | ✅ Yes | Review/Migrate |
| `static/onboarding/` | 6 | ✅ Yes | Review |
| `static/public/` | 8 | ✅ Yes | Keep |
| `static/tenant/` | 7 | ✅ Yes | Review |
| `static/templates/` | 3 | ✅ Yes | **Delete** |
| `staticbac/` | 50+ | ❌ **No** | **DELETE** |
| `modules/core/templates/` | 3 | ✅ Yes | **Merge** |
| `semptify_dakota_eviction/templates/` | 7+ | ✅ Yes | Separate project |
| `design-system/` | 15 | ✅ Yes | Keep |

### **TOTAL: ~110 HTML Files**

**Recommended Actions:**
- **Keep:** ~40 files (active templates, design system)
- **Merge:** ~15 files (consolidate duplicates)
- **Delete:** ~55 files (backups, legacy, duplicates)

---

*Document generated for consolidation planning. Execute phases sequentially.*
*Last updated: May 22, 2026 - Includes untracked/backup files analysis*
