# Template Consolidation Reference Model
**Purpose:** Complete mapping for planning - NO implementation
**Status:** Reference Only - Review before any changes

---

## Part 1: Page Ecosystems (What Exists Now)

### 1.1 Welcome Page Ecosystem

| Location | Tech | Theme | Size | Content Style |
|----------|------|-------|------|---------------|
| `app/templates/pages/welcome.html` | Jinja2 | Dark | 631 lines | Process-driven, SSOT API |
| `static/welcome.html` | Static | Light/serif | 646 lines | Article format, marketing |
| `static/public/welcome.html` | Static | Light | 702 lines | SSOT features, checkpoint |
| `staticbac/badwelcome.html` | Static | Unknown | 42KB | Legacy version |

**Consolidation Target:** Single `welcome.html` (Jinja2) with:
- Dark theme (authenticated version)
- SSOT navigation features from public version
- Article content flow from static version

---

### 1.2 Library Page Ecosystem

| Location | Tech | Features | Size |
|----------|------|----------|------|
| `app/templates/pages/library.html` | Jinja2 | Macro-based cards | 33 lines |
| `static/library.html` | Static | Full resource grid, state API | 536 lines |
| `static/tenant/law-library.html` | Static | Comprehensive law reference | 879 lines |
| `staticbac/law_library.html` | Static | Legacy version | 54KB |

**Consolidation Target:** Two-tier system
- `/library` → Hub (merge A + B features)
- `/law-library` → Deep reference (use C content)

---

### 1.3 Office Page Ecosystem

| Location | Tech | Features | Size |
|----------|------|----------|------|
| `app/templates/pages/office.html` | Jinja2 | Minimal macro-based | 46 lines |
| `static/office.html` | Static | Full cards, vault CTA | 198 lines |

**Consolidation Target:** Single Jinja2 template with:
- Macro structure from app version
- Vault CTA component from static version
- Card grid from static version

---

### 1.4 Home/Dashboard Ecosystem

| Location | Tech | Purpose | Size |
|----------|------|---------|------|
| `app/templates/pages/tenant_home.html` | Jinja2 | Auth landing | 194 lines |
| `app/templates/pages/tenant_dashboard.html` | Jinja2 | Full dashboard | 520 lines |
| `static/home.html` | Static | Marketing + dash hybrid | 383 lines |
| `static/tenant/dashboard.html` | Static | Comprehensive dash | 21,395 lines |

**Consolidation Target:** Clear hierarchy
- `/home` → Marketing (light theme, static or Jinja2)
- `/tenant/home` → Auth home (merge B + C concepts)
- `/tenant/dashboard` → Full dashboard (reference D for features)

---

### 1.5 Base Template Ecosystem

| Location | Tech | Lines | Theme | Extends |
|----------|------|-------|-------|---------|
| `app/templates/base.html` | Jinja2 | 614 | Dark | None (root) |
| `modules/core/templates/base.html` | Jinja2 | 83 | Auto | None |
| `static/templates/base.html` | HTML | 166 | Ocean | None |
| `staticbac/` | HTML | various | various | None |

**Consolidation Target:** Single canonical base.html
- Dark theme default
- Light theme conditional
- All other bases deleted

---

## Part 2: Route-to-File Mapping

### Current State (Before Consolidation)

```
ROUTE                    → FILE (Current)
───────────────────────────────────────────────────────
/                        → app/templates/pages/welcome.html
                         [+ static/welcome.html (shadow?)]
                         [+ static/public/welcome.html]

/home                    → static/home.html (if exists)
                         [or app/templates/pages/tenant_home.html]

/library                 → app/templates/pages/library.html
                         [+ static/library.html (shadow)]

/law-library             → static/tenant/law-library.html

/office                  → app/templates/pages/office.html
                         [+ static/office.html (shadow)]

/documents               → app/templates/pages/documents.html
/vault                   → app/templates/pages/vault.html
/timeline                → app/templates/pages/timeline.html
/help                    → app/templates/pages/help.html
/tools                   → app/templates/pages/tools.html

/tenant/*                → app/templates/pages/tenant_*.html
/advocate/*              → app/templates/pages/advocate.html
/legal/*                 → app/templates/pages/legal.html
/admin/*                 → app/templates/pages/admin.html

/static/*                → static/ (various)
/staticbac/*             → NOT SERVED (backup folder)
```

### Target State (After Consolidation)

```
ROUTE                    → FILE (Target)
───────────────────────────────────────────────────────
/                        → app/templates/pages/welcome.html
                         [ONLY - static versions deleted]

/home                    → app/templates/pages/home.html
                         [merged marketing version]

/library                 → app/templates/pages/library.html
                         [merged with static features]

/law-library             → static/tenant/law-library.html
                         [OR move to app/templates/pages/]

/office                  → app/templates/pages/office.html
                         [merged with static features]

/documents               → app/templates/pages/documents.html
/vault                   → app/templates/pages/vault.html
/timeline                → app/templates/pages/timeline.html
/help                    → app/templates/pages/help.html
/tools                   → app/templates/pages/tools.html

/tenant/*                → app/templates/pages/tenant_*.html
/advocate/*              → app/templates/pages/advocate.html
/legal/*                 → app/templates/pages/legal.html
/admin/*                 → app/templates/pages/admin.html

/static/public/*         → static/public/ (marketing only)
/static/onboarding/*     → Keep or migrate
/static/templates/*      → DELETED
/staticbac/*             → DELETED
```

---

## Part 3: Feature Migration Matrix

### Features to Migrate (From Static → Jinja2)

| Source File | Feature | Target File | Complexity |
|-------------|---------|-------------|------------|
| static/library.html | State law API dropdown | app/templates/pages/library.html | Medium |
| static/library.html | Resource card grid | app/templates/pages/library.html | Low |
| static/library.html | Category tabs | app/templates/pages/library.html | Low |
| static/office.html | Vault CTA component | app/templates/pages/office.html | Low |
| static/office.html | Primary actions grid | app/templates/pages/office.html | Medium |
| static/office.html | Sub-nav quick links | app/templates/pages/office.html | Low |
| static/public/welcome.html | SSOT navigation JS | app/templates/pages/welcome.html | Medium |
| static/public/welcome.html | Checkpoint cookie | app/templates/pages/welcome.html | Low |
| static/tenant/dashboard.html | Dashboard widgets | app/templates/pages/tenant_dashboard.html | High |
| static/tenant/law-library.html | Law reference content | Keep separate OR merge | High |

### Features to Drop (Not Migrating)

| Source File | Feature | Reason |
|-------------|---------|--------|
| static/welcome.html | Serif typography | Not on-brand |
| static/welcome.html | Article layout | Use process layout |
| staticbac/* | All features | Legacy, replaced |

---

## Part 4: Visual Design Consolidation

### Color System Unification

**Current State (4 systems):**

| Source | Primary | Accent | Background |
|--------|---------|--------|------------|
| Jinja2 dark | `#1a1a2e` | `#3b82f6` | gradient |
| Static light | `#1a237e` | `#3949ab` | white |
| Welcome warm | `#1e3a5f` | `#3b82f6` | paper |
| Tenant purple | `#4c1d95` | `#7c3aed` | light |

**Target State (2 systems):**

| Theme | Use Case | Primary | Accent | Background |
|-------|----------|---------|--------|------------|
| Dark | Authenticated | `#1a1a2e` | `#3b82f6` | gradient |
| Light | Public/Marketing | `#1e3a5f` | `#3b82f6` | paper |

### Typography Unification

| Use Case | Current | Target |
|----------|---------|--------|
| App UI | Inter / system-ui | Inter only |
| Marketing | Georgia / serif | Inter (or keep serif for editorial) |
| Content-heavy | system-ui | Inter |

---

## Part 5: Component Inventory

### Reusable Components (Keep)

| Component | Location | Used In | Status |
|-----------|----------|---------|--------|
| ui_macros.html | components/ | library, office, tools, help | Keep |
| upload_zone.html | components/ | documents | Keep |
| functions_bar.html | components/ | tenant pages | Keep |
| document_card.html | components/ | documents | Keep |

### Components to Merge/Consolidate

| Component | Current State | Target |
|-----------|---------------|--------|
| Vault sidebar | 3 versions in design-system/ | Single canonical version |
| Dashboard widgets | Multiple implementations | Unified component |
| Navigation | 4 different nav bars | Single nav component |
| Footer | Multiple implementations | unified-footer-loader.js |

### Design System Components (Reference)

All in `design-system/components/function-groups/`:
- capture/ (4 components)
- vault/ (3 components)
- understand/ (3 components)
- plan/ (3 components)
- role-specific/ (6 components)
- onboarding/ (3 components)

**Action:** Keep all, standardize styling to match unified theme.

---

## Part 6: Deletion Candidates

### Tier 1: Safe to Delete (No Migration Needed)

| File/Folder | Reason | Size |
|-------------|--------|------|
| `staticbac/` | Legacy backup, not tracked | ~5MB |
| `static/templates/base.html` | Duplicate of app version | 166 lines |
| `static/onboarding/*.bak` | Backup files | 2 files |
| `staticbac/admin/gui_navigation_hub.html` | Dead purple UI | 736 lines |
| `staticbac/badwelcome.html` | Superseded | 42KB |
| `staticbac/auto_mode_demo.html` | Already deleted | 18KB |
| `staticbac/batch_analysis_results.html` | Already deleted | 17KB |
| `staticbac/my_tenancy.html` | Covered by tenant_home | 10KB |

### Tier 2: Delete After Feature Migration

| File | Migrate These Features | Then Delete |
|------|------------------------|-------------|
| `static/welcome.html` | Content structure | Yes |
| `static/library.html` | Card grid, state API | Yes |
| `static/office.html` | Vault CTA, actions | Yes |
| `static/home.html` | Marketing content | Yes |

### Tier 3: Review Before Deletion

| File | Contains | Decision |
|------|----------|----------|
| `static/tenant/dashboard.html` | 21K lines, comprehensive | Keep as reference OR extract features |
| `static/tenant/law-library.html` | 879 lines, law content | Keep as `/law-library` OR migrate content |
| `static/tenant/documents.html` | 17K lines, vault features | Extract features to app version |

---

## Part 7: Consolidation Phases (For Planning)

### Phase 0: Cleanup (No Risk)
1. Delete `staticbac/` folder
2. Delete `.bak` files
3. Delete `static/templates/` (duplicate base.html)

### Phase 1: Welcome Consolidation
1. Review 3 welcome versions
2. Document features to migrate
3. Plan single welcome.html structure
4. Schedule migration

### Phase 2: Library Consolidation
1. Merge static/library.html features into Jinja2 version
2. Keep or migrate law-library.html
3. Update routes

### Phase 3: Office Consolidation
1. Migrate static/office.html features
2. Update vault CTA component
3. Standardize card grid

### Phase 4: Base Template Unification
1. Merge 4 base.html versions
2. Implement theme switching
3. Update all child templates

### Phase 5: Dashboard Optimization
1. Review 21K line tenant dashboard
2. Extract reusable components
3. Merge with Jinja2 version

---

## Part 8: Reference Tables

### File Size Comparison

| File | Lines | Type | Priority |
|------|-------|------|----------|
| static/tenant/dashboard.html | 21,395 | Static | Review |
| staticbac/briefcase.html | 2,694 | Legacy | Delete |
| static/tenant/law-library.html | 879 | Static | Review |
| static/library.html | 536 | Static | Migrate |
| app/templates/pages/tenant_dashboard.html | 520 | Jinja2 | Keep |
| static/home.html | 383 | Static | Migrate |
| static/welcome.html | 646 | Static | Migrate |
| static/public/welcome.html | 702 | Static | Migrate |
| app/templates/pages/welcome.html | 631 | Jinja2 | Keep |
| static/office.html | 198 | Static | Migrate |
| app/templates/pages/office.html | 46 | Jinja2 | Keep |
| app/templates/pages/library.html | 33 | Jinja2 | Keep |

### Route Conflicts

| Route | Files Claiming It | Resolution |
|-------|-------------------|------------|
| `/` | welcome.html (3 versions) | Use Jinja2, delete static |
| `/library` | library.html (2 versions) | Use Jinja2, migrate features |
| `/office` | office.html (2 versions) | Use Jinja2, migrate features |
| `/home` | home.html (2+ versions) | Clarify hierarchy |

### SSOT Navigation Registry Check

| Stage ID | Current Path | Template | Valid? |
|----------|--------------|----------|--------|
| welcome | `/` | welcome.html | ✅ |
| role_select | `/onboarding/select-role.html` | select-role.html | Check static |
| providers | `/storage/providers` | Jinja2 | ✅ |
| tenant_home | `/home` | tenant_home.html | Check route |
| library | `/library` | library.html | Check static shadow |
| office | `/office` | office.html | Check static shadow |

---

## Part 9: Decision Matrix

### For Each Duplicate Set, Decide:

| Duplicate Set | Decision Options | Recommendation |
|---------------|------------------|----------------|
| Welcome (3x) | A) Keep all B) Merge to Jinja2 C) Keep static | **B** - Merge to Jinja2 |
| Library (4x) | A) Single page B) Hub + deep ref C) Keep all | **B** - Hub + deep ref |
| Office (2x) | A) Merge to Jinja2 B) Keep static C) Keep both | **A** - Merge to Jinja2 |
| Home (4x) | A) Clear hierarchy B) Merge all C) Keep all | **A** - Clear hierarchy |
| Base (4x) | A) Merge to one B) Keep multiple C) Delete all but one | **A** - Merge to one |

---

## Part 10: Quick Reference Card

### Current File Count by Status

| Status | Count | Examples |
|--------|-------|----------|
| Keep (Jinja2) | 25 | app/templates/pages/*.html |
| Keep (Static public) | 8 | static/public/*.html |
| Migrate then Delete | 4 | static/{welcome,library,office,home}.html |
| Delete (Legacy) | 50+ | staticbac/* |
| Review | 3 | static/tenant/{dashboard,law-library,documents}.html |
| Merge | 3 | base.html versions |

### Risk Assessment

| Action | Risk | Mitigation |
|--------|------|------------|
| Delete staticbac/ | **None** | Not tracked, not served |
| Delete .bak files | **None** | Explicit backups |
| Merge welcome pages | Low | Keep backups until verified |
| Merge base.html | Medium | Test all child pages |
| Migrate static/library | Low | Feature comparison first |

---

**END OF REFERENCE MODEL**

*This document is for planning purposes only. No files have been modified.*
*Use this reference to plan implementation phases.*
