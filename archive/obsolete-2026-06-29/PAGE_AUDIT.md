# PAGE AUDIT — Semptify GUI

**Date:** 2026-06-22  
**Auditor:** Cascade (AI) + User  
**Purpose:** Blueprint for GUI scaffolding redesign. Every page must justify its existence.

---

## How To Read This Audit

Each page is scored on:

- **Purpose:** Why does it exist? (one sentence)
- **Tier:** Which product tier does it serve?
- **Division:** Which user division does it belong to?
- **Status:** Live / Stub / Dead / Duplicate
- **Route:** URL that serves it
- **Template:** Jinja file or static HTML file
- **Issues:** Problems found
- **Verdict:** Keep / Merge / Delete / Rewrite

---

## TIER MAP (from `product_manifest.py`)

| Tier | Purpose | Serves |
| ------ | --------- | -------- |
| CORE | Tenant-rights essentials | Tenants |
| EXTENDED | Legal tools | Tenants needing court prep |
| ADVOCATE | Advocate network | Advocates, attorneys |
| ADMIN | Dashboards, analytics | Admins |
| RESEARCH | AI intelligence | System, admins |
| DEV | Internal tools | Developers |

---

## DIVISION MAP (proposed)

| Division | User | Pages belong here |
| ---------- | ------ | ------------------- |
| **Tenant** | The person facing housing problems | Dashboard, Journal, Documents, Timeline, Inbox, Capture, Help, Home |
| **Advocate** | The helper | Dashboard, Clients, Case Queue, Intake, Timeline |
| **Office** | Tools for getting things done | Vault, Signer, Delivery, Generators, Calculators, Checklists |
| **Admin** | Running the platform | Dashboard, Dev Lab, Module Flags, Review, Manual, Workbook |
| **Public** | Anyone (no auth) | Welcome, Help, Library, Search |

---

## JINJA TEMPLATES (27 files in `app/templates/pages/`)

### 1. `semptify_hub.html` (353 lines, 13.6KB)

- **Route:** `/home`
- **Purpose:** Tenant home page — "your home, your documents, your rights"
- **Tier:** CORE
- **Division:** Tenant
- **Status:** Live
- **Issues:** Has its own inline styles. Zone tabs concept. Duplicates tenant_home purpose.
- **Verdict:** **MERGE** with `tenant_home.html` — one home page, not two.

### 2. `tenant_home.html` (463 lines, 13.1KB)

- **Route:** `/tenant/home` (likely)
- **Purpose:** "Your safe space to organize your housing situation"
- **Tier:** CORE
- **Division:** Tenant
- **Status:** Live
- **Issues:** Duplicates `semptify_hub.html` purpose. Welcome section with gradients (soft/rounded).
- **Verdict:** **MERGE** with `semptify_hub.html`.

### 3. `tenant_dashboard.html` (557 lines, 21.3KB)

- **Route:** `/tenant/dashboard`
- **Purpose:** Main tenant dashboard with modular components
- **Tier:** CORE
- **Division:** Tenant
- **Status:** Live (static HTML file in `static/tenant/dashboard.html` is also served)
- **Issues:** Standalone HTML, doesn't extend `base.html`. Has its own gradient header. 320px right sidebar for vault.
- **Verdict:** **REWRITE** — extend `tenant_base.html`, integrate with overlay system.

### 4. `tenant.html` (85 lines, 2.6KB)

- **Route:** `/tenant` (likely)
- **Purpose:** "My Case" — role grid with links
- **Tier:** CORE
- **Division:** Tenant
- **Status:** Live but minimal
- **Issues:** Just a link grid. No real content. Could be merged with dashboard.
- **Verdict:** **MERGE** into tenant dashboard as a navigation panel.

### 5. `tenant_capture.html` (10.9KB)

- **Route:** `/tenant/capture`
- **Purpose:** Document capture tool
- **Tier:** CORE
- **Division:** Tenant (or Office)
- **Status:** Live
- **Issues:** Unclear if this is the upload flow or a separate capture tool.
- **Verdict:** **KEEP** — needs purpose clarification.

### 6. `tenant_help.html` (16.4KB)

- **Route:** `/tenant/help`
- **Purpose:** Tenant rights guide
- **Tier:** CORE
- **Division:** Tenant
- **Status:** Live
- **Issues:** Overlaps with `help.html` and `library.html`.
- **Verdict:** **KEEP** — this is the rights guide, distinct from platform help.

### 7. `tenant_inbox.html` (8.9KB)

- **Route:** `/tenant/inbox`
- **Purpose:** Tenant messaging inbox
- **Tier:** CORE
- **Division:** Tenant
- **Status:** Live
- **Issues:** None major.
- **Verdict:** **KEEP**.

### 8. `tenant_journal.html` (7.9KB)

- **Route:** `/tenant/journal`
- **Purpose:** Tenant journal entries
- **Tier:** CORE
- **Division:** Tenant
- **Status:** Live
- **Issues:** Overlaps with `timeline.html`.
- **Verdict:** **CLARIFY** — is journal different from timeline? If yes, keep both. If no, merge.

### 9. `timeline.html` (12.8KB)

- **Route:** `/timeline`
- **Purpose:** Chronological record of events
- **Tier:** CORE
- **Division:** Tenant (but also used by advocates)
- **Status:** Live
- **Issues:** Cross-division use. Should be accessible from both Tenant and Advocate divisions.
- **Verdict:** **KEEP** — shared component across divisions.

### 10. `documents.html` (6.3KB)

- **Route:** `/documents`
- **Purpose:** Document vault view
- **Tier:** CORE
- **Division:** Office (or Tenant)
- **Status:** Live
- **Issues:** Overlaps with `vault.html`. Which is the real vault UI?
- **Verdict:** **CLARIFY** — documents vs vault. One should be the canonical vault UI.

### 11. `vault.html` (15KB)

- **Route:** `/vault`
- **Purpose:** Vault UI page (post-OAuth)
- **Tier:** CORE
- **Division:** Office
- **Status:** Live
- **Issues:** Overlaps with `documents.html`. Has fallback HTML embedded in `main.py`.
- **Verdict:** **CLARIFY** — merge with documents or make vault the canonical UI.

### 12. `office.html` (46 lines, 2.1KB)

- **Route:** `/office`
- **Purpose:** Office hub — case management center
- **Tier:** CORE
- **Division:** Office
- **Status:** Live
- **Issues:** Just a card grid linking to other pages. No real functionality.
- **Verdict:** **KEEP** — serves as division landing page.

### 13. `tools.html` (34 lines, 1.7KB)

- **Route:** `/tools`
- **Purpose:** Tools hub — document generators and utilities
- **Tier:** CORE
- **Division:** Office
- **Status:** Live
- **Issues:** Just a card grid. Links to tools that live in `static/tools/`.
- **Verdict:** **KEEP** — serves as division landing page.

### 14. `library.html` (33 lines, 1.7KB)

- **Route:** `/library`
- **Purpose:** Library hub — legal resources
- **Tier:** CORE
- **Division:** Public
- **Status:** Live
- **Issues:** Just a card grid. Links to `law_library.html` which is the real library.
- **Verdict:** **KEEP** — serves as division landing page.

### 15. `law_library.html` (1414 lines, 157.5KB)

- **Route:** `/law-library`
- **Purpose:** Minnesota law library — statutes, constitution, cases
- **Tier:** CORE
- **Division:** Public
- **Status:** Live
- **Issues:** **157KB single file.** Unmaintainable. Has its own dark theme. Should be split into 8+ pages. Has Eviction Answer wizard inline.
- **Verdict:** **REWRITE** — split into: library home, constitution, federal, minnesota, local, procedures, state lookup, eviction answer.

### 16. `help.html` (42 lines, 2.2KB)

- **Route:** `/help`
- **Purpose:** Platform help and support
- **Tier:** CORE
- **Division:** Public
- **Status:** Live
- **Issues:** Overlaps with `tenant_help.html` and `static/help.html` (46KB).
- **Verdict:** **CLARIFY** — three help pages is two too many.

### 17. `welcome.html` (24.6KB)

- **Route:** `/welcome`
- **Purpose:** Welcome page for new users
- **Tier:** CORE
- **Division:** Public
- **Status:** Live
- **Issues:** Large file. Onboarding flow entry point.
- **Verdict:** **KEEP** — onboarding is critical.

### 18. `admin.html` (92 lines, 2.8KB)

- **Route:** `/admin` (redirects to dashboard)
- **Purpose:** Admin role grid
- **Tier:** ADMIN
- **Division:** Admin
- **Status:** Live but minimal
- **Issues:** Just a link grid. The real admin dashboard is `static/admin/dashboard.html` (84KB).
- **Verdict:** **MERGE** — redirect or embed in admin dashboard.

### 19. `advocate.html` (193 lines, 9.6KB)

- **Route:** `/advocate/dashboard`
- **Purpose:** Advocate dashboard with clients, case queue, stats
- **Tier:** ADVOCATE
- **Division:** Advocate
- **Status:** Live
- **Issues:** Has its own inline styles. Fetches from advocate API endpoints.
- **Verdict:** **KEEP** — needs to extend `advocate_base.html`.

### 20. `manager_dashboard.html` (212 lines, 10.3KB)

- **Route:** `/manager/dashboard`
- **Purpose:** Multi-tenant case oversight for agencies
- **Tier:** ADVOCATE (or its own)
- **Division:** Advocate
- **Status:** Live
- **Issues:** Has its own CSS file (`manager-dashboard.css`).
- **Verdict:** **KEEP** — needs to extend `advocate_base.html`.

### 21. `legal.html` (89 lines, 2.8KB)

- **Route:** `/legal/dashboard`
- **Purpose:** Legal dashboard — role grid
- **Tier:** EXTENDED
- **Division:** Advocate (or its own Legal division)
- **Status:** Live but minimal
- **Issues:** Just a link grid. No real legal tools yet.
- **Verdict:** **KEEP** — needs real content.

### 22. `case_builder.html` (339 lines, 9.8KB)

- **Route:** `/case-builder`
- **Purpose:** Organize documents and evidence for a case
- **Tier:** EXTENDED
- **Division:** Tenant (or Advocate)
- **Status:** Live
- **Issues:** Unclear if this is different from timeline + documents + vault.
- **Verdict:** **CLARIFY** — what does case builder do that timeline + vault don't?

### 23. `complaints.html` (276 lines, 8.6KB)

- **Route:** `/complaints`
- **Purpose:** Where to file housing complaints in MN
- **Tier:** CORE
- **Division:** Public (or Tenant)
- **Status:** Live
- **Issues:** Static information page. Could be in library.
- **Verdict:** **MERGE** into library.

### 24. `action_plan.html` (335 lines, 10.8KB)

- **Route:** `/action-plan`
- **Purpose:** Prioritized next steps for a housing case
- **Tier:** CORE
- **Division:** Tenant
- **Status:** Live
- **Issues:** Good concept. Should be on the tenant dashboard.
- **Verdict:** **MERGE** into tenant dashboard as a panel.

### 25. `auto_mode_panel.html` (435 lines, 12.9KB)

- **Route:** `/auto-mode`
- **Purpose:** Auto Mode control panel
- **Tier:** DEV
- **Division:** Admin
- **Status:** Live
- **Issues:** Purple gradient header. Dev tool.
- **Verdict:** **KEEP** — admin only.

### 26. `auto_analysis_summary.html` (366 lines, 9.7KB)

- **Route:** `/auto-analysis`
- **Purpose:** Auto analysis summary
- **Tier:** DEV
- **Division:** Admin
- **Status:** Live
- **Issues:** Purple gradient header. Dev tool.
- **Verdict:** **KEEP** — admin only.

### 27. `module_page.html` (288 lines, 6.9KB)

- **Route:** Dynamic (module pages)
- **Purpose:** Generic module page template
- **Tier:** All
- **Division:** All
- **Status:** Live
- **Issues:** Good concept — one template for all module pages.
- **Verdict:** **KEEP** — this is the right pattern.

### 28. `error.html` (1267 bytes)

- **Route:** Error pages
- **Purpose:** Error display
- **Tier:** All
- **Division:** All
- **Status:** Live
- **Issues:** None.
- **Verdict:** **KEEP**.

---

## STATIC HTML PAGES (in `static/`)

### `static/home.html` (21.6KB)

- **Route:** Served by `/home` fallback?
- **Purpose:** Static home page
- **Status:** **DUPLICATE** — `/home` route serves `semptify_hub.html` template.
- **Verdict:** **DELETE** — dead duplicate.

### `static/welcome.html` (21.5KB)

- **Route:** `/welcome.html`
- **Purpose:** Static welcome page
- **Status:** **DUPLICATE** — `welcome.html` template exists.
- **Verdict:** **DELETE** — dead duplicate.

### `static/help.html` (46KB) + `static/help_old.html` (43.9KB)

- **Route:** `/help` fallback?
- **Purpose:** Static help page
- **Status:** **DUPLICATE** — `/help` route serves `help.html` template.
- **Verdict:** **DELETE BOTH** — dead duplicates.

### `static/office.html` (12KB)

- **Route:** `/office` fallback?
- **Purpose:** Static office page
- **Status:** **DUPLICATE** — `/office` route serves `office.html` template.
- **Verdict:** **DELETE** — dead duplicate.

### `static/library.html` (29.8KB)

- **Route:** `/library` fallback?
- **Purpose:** Static library page with context panels
- **Status:** **DUPLICATE** — `/library` route serves `library.html` template. BUT has Context Engine panels wired in.
- **Verdict:** **CLARIFY** — move context panels to the Jinja template, then delete this.

### `static/tools.html` (20.7KB)

- **Route:** `/tools` fallback?
- **Purpose:** Static tools page
- **Status:** **DUPLICATE** — `/tools` route serves `tools.html` template.
- **Verdict:** **DELETE** — dead duplicate.

### `static/search.html` (19KB)

- **Route:** `/search`?
- **Purpose:** Search page
- **Status:** Live
- **Issues:** Not in main nav. Orphan page.
- **Verdict:** **CLARIFY** — is this used? If not, delete.

### `static/filedored.html` (10.6KB)

- **Route:** `/filedored`?
- **Purpose:** Filedored (virtual folder) UI
- **Status:** Live
- **Issues:** Not in main nav. Orphan page.
- **Verdict:** **CLARIFY** — should be in Office division.

### `static/tenant/` (8 items)

- `dashboard.html` — **DUPLICATE** of `tenant_dashboard.html` template
- `journal.html` — **DUPLICATE** of `tenant_journal.html` template
- `documents.html` — **DUPLICATE** of `documents.html` template
- `tools/deadlines.html`, `tools/letters.html` — Live tools
- **Verdict:** **CLARIFY** — which versions are actually served?

### `static/admin/` (11 items)

- `dashboard.html` (84KB) — **Live** — the real admin dashboard
- `dev_lab.html`, `module_flags.html`, `review-checklist.html` — Live
- `api_workbook.html`, `contract-browser.html`, `function-browser.html` — Live
- `manual.html`, `page-editor.html` — Live
- `home.html`, `login.html` — Live
- **Verdict:** **KEEP** — these are the real admin pages. Need to extend `admin_base.html`.

### `static/office/` (4 items)

- `inbox.html`, `signer.html`, `delivery.html`, `vault.html` — Live
- **Verdict:** **KEEP** — need to extend `office_base.html`.

### `static/tools/` (3 items)

- `generators.html`, `checklists.html`, `calculators.html` — Live
- **Verdict:** **KEEP** — need to extend `office_base.html`.

### `static/advocate/` (2 items)

- `dashboard.html` — **DUPLICATE** of `advocate.html` template
- **Verdict:** **CLARIFY**.

### `static/manager/` (2 items)

- `dashboard.html` — **DUPLICATE** of `manager_dashboard.html` template
- **Verdict:** **CLARIFY**.

### `static/legal/` (2 items)

- **Verdict:** **CHECK** — likely stubs.

### `static/onboarding/` (11 items)

- Onboarding flow pages
- **Verdict:** **KEEP** — onboarding is critical.

### `static/public/` (8 items)

- Public pages including `welcome.html`
- **Verdict:** **CLARIFY** — duplicates with templates?

### `static/mndes/` (2 items)

- MNDES (Minnesota Digital Evidence System) pages
- **Verdict:** **KEEP** — court exhibit compliance.

### `static/templates/` (4 items)

- **Verdict:** **CHECK** — likely dead.

---

## DEAD PAGES TO DELETE IMMEDIATELY

| File | Reason | Status |
| ------ | -------- | -------- |
| `static/home.html` | Duplicate of `semptify_hub.html` template | ✅ DELETED 2026-06-23 |
| `static/welcome.html` | Duplicate of `welcome.html` template | ✅ DELETED 2026-06-23 |
| `static/help.html` | Duplicate of `help.html` template | ✅ DELETED 2026-06-23 |
| `static/help_old.html` | Old version of help | ✅ DELETED 2026-06-23 |
| `static/office.html` | Duplicate of `office.html` template | ✅ DELETED 2026-06-23 |
| `static/tools.html` | Duplicate of `tools.html` template | ✅ DELETED 2026-06-23 |
| `app/templates/journal-refactored.html` | Dead template, never referenced | ✅ Already absent |

### 6 files deleted (1 already gone). Saved ~165KB of dead code

### References Fixed Before Deletion

- `app/services/action_router.py:383` — `/static/help.html` → `/help`
- `app/modules/storage/router.py:2485` — `/static/welcome.html` → `/welcome`
- `app/core/page_manifest.py:1498` — `static/help.html` → `app/templates/pages/help.html` (jinja)
- `app/core/page_manifest.py:2098` — `static/home.html` → `app/templates/pages/semptify_hub.html` (jinja)

---

## DUPLICATE PAGES TO MERGE

| Keep | Delete | Reason |
| ------ | -------- | -------- |
| `semptify_hub.html` | `tenant_home.html` | Same purpose: tenant home |
| `tenant_dashboard.html` | `tenant.html` | Dashboard supersedes link grid |
| `documents.html` | `vault.html` | Both are vault UI — pick one |
| `help.html` | `tenant_help.html` | Clarify: platform help vs rights guide |
| `library.html` (Jinja) | `complaints.html` | Complaints belong in library |

---

## PROPOSED DIVISION STRUCTURE

### Tenant Division

```text
tenant_base.html (extends base.html)
├── dashboard.html    ← merges tenant_dashboard + action_plan + tenant.html
├── journal.html      ← tenant_journal (if different from timeline)
├── documents.html    ← merges documents + vault
├── timeline.html     ← shared with advocate
├── inbox.html        ← tenant_inbox
├── capture.html      ← tenant_capture
└── help.html         ← tenant_help (rights guide)
```

### Advocate Division

```text
advocate_base.html (extends base.html)
├── dashboard.html    ← advocate.html
├── manager.html      ← manager_dashboard.html
├── legal.html        ← legal.html
├── case_builder.html ← case_builder.html
└── timeline.html     ← shared with tenant
```

### Office Division

```text
office_base.html (extends base.html)
├── vault.html        ← canonical vault UI
├── signer.html       ← static/office/signer.html
├── delivery.html     ← static/office/delivery.html
├── inbox.html        ← static/office/inbox.html
├── generators.html   ← static/tools/generators.html
├── checklists.html   ← static/tools/checklists.html
├── calculators.html  ← static/tools/calculators.html
└── filedored.html    ← static/filedored.html
```

### Admin Division

```text
admin_base.html (extends base.html)
├── dashboard.html    ← static/admin/dashboard.html (split into components)
├── dev_lab.html      ← static/admin/dev_lab.html
├── module_flags.html ← static/admin/module_flags.html
├── review.html       ← static/admin/review-checklist.html
├── manual.html       ← static/admin/manual.html
├── workbook.html     ← static/admin/api_workbook.html
├── contracts.html    ← static/admin/contract-browser.html
├── functions.html    ← static/admin/function-browser.html
├── page_editor.html  ← static/admin/page-editor.html
├── auto_mode.html    ← auto_mode_panel.html
└── auto_analysis.html← auto_analysis_summary.html
```

### Public Division

```text
public_base.html (extends base.html, no sidebar)
├── welcome.html      ← onboarding entry
├── library.html      ← library hub
├── law_library.html  ← SPLIT into 8 pages
├── help.html         ← platform help
└── search.html       ← if kept
```

---

## OVERLAY SYSTEM STATUS

### Status: BUILT, not exposed in GUI

The `UnifiedOverlayManager` (566 lines) is live with 20 overlay types:

- Upload manifests
- Document extraction, classification, timeline extraction
- Highlights, notes, footnotes, tracked edits
- Form fill, signatures
- Court packet queries, evidence bundle queries
- PII redaction
- Identity adapters, communication, filedored, duplicate detection

**The GUI doesn't expose any of this to users.** Tenants can't:

- See overlays on their documents
- Add highlights or notes
- View classifications
- Toggle overlay layers
- See extraction results

**This is the biggest GUI gap.** The backend is a Chevrolet; the dashboard doesn't show the engine.

---

## TECHNICAL DEBT SUMMARY

| Category | Count | Severity |
| ---------- | ------- | ---------- |
| Dead pages | 7 | Low (delete) |
| Duplicate pages | 5 pairs | Medium (merge) |
| Pages > 50KB | 3 | High (split) |
| Pages with inline styles | 20+ | Medium |
| Pages not extending base.html | 15+ | High |
| Orphan pages (not in nav) | 3 | Medium |
| Overlay types not in GUI | 20 | High |

---

## RECOMMENDED EXECUTION ORDER

1. **Delete 7 dead pages** (30 min)
2. **Merge 5 duplicate pairs** (2 hr)
3. **Build 5 division base templates** (3 hr)
4. **Migrate pages to division templates** (5 sessions)
5. **Split law_library.html into 8 pages** (1 session)
6. **Split admin/dashboard.html into components** (1 session)
7. **Build overlay viewer GUI** (2 sessions)
8. **Apply professional design language** (1 session)
9. **Performance pass** (1 session)

---

## OPEN QUESTIONS FOR USER

1. **Journal vs Timeline** — are these different things? Journal = personal notes? Timeline = legal events?
2. **Documents vs Vault** — which is the canonical vault UI?
3. **Help vs Tenant Help** — platform help vs rights guide?
4. **Case Builder** — what does it do that timeline + vault don't?
5. **Search page** — is it used? Should it be in nav?
6. **Filedored** — should it be in Office division?
7. **Manager vs Advocate** — are these the same division or separate?

---

*End of audit. This document is the blueprint for the GUI scaffolding redesign.*
