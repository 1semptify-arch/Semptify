# Semptify Complete Page & User Flow Inventory

**Generated:** December 21, 2025  
**Total HTML Files:** 105 (83 active, 22 archived/duplicates)  
**Total API Routers:** 55+  

---

## 🚨 EXECUTIVE SUMMARY

### Critical Issues Found:
1. **TOO MANY ENTRY POINTS** - 6 different "welcome/home" pages
2. **DUPLICATE FUNCTIONALITY** - Multiple document, timeline, and dashboard versions
3. **FRAGMENTED USER JOURNEYS** - No clear single path through the app
4. **ROLE CONFUSION** - 5 different role-based interfaces that overlap
5. **FEATURE SPRAWL** - 80+ pages for what should be a focused tenant tool

### Recommended Actions:
1. **Consolidate to ONE entry point** → `welcome.html` or `index.html`
2. **Remove v2/backup versions** - Keep only one version of each page
3. **Simplify roles** - Tenant is primary, advocate/legal are secondary
4. **Focus on core workflow** - Document → Timeline → Defense → Court

---

## 📂 COMPLETE HTML FILE LIST

### 🏠 ENTRY POINTS (DUPLICATES - NEEDS CONSOLIDATION)

| File | Purpose | Status |
|------|---------|--------|
| `index.html` | "Elbow" tenant assistant UI | **ALTERNATIVE BRAND** |
| `home.html` | Simple "Get Started" page | **ORPHANED** |
| `welcome.html` | "The Tenant's Journal" landing | **PRIMARY** |
| `onboarding/welcome.html` | Minnesota-focused onboarding | **DUPLICATE** |
| `complete-journey.html` | Full onboarding wizard | **DUPLICATE** |
| `crisis_intake.html` | Crisis mode intake | **SPECIALIZED** |

**🔧 FIX:** Merge into single `index.html` → role selection → dashboard

---

### 📊 DASHBOARDS (4 VERSIONS!)

| File | Purpose | Status |
|------|---------|--------|
| `dashboard.html` | Command Center (2675 lines!) | **BLOATED** |
| `dashboard-v2.html` | Simplified dashboard | **KEEP** |
| `command_center.html` | Dakota County defense hub | **SPECIALIZED** |
| `enterprise-dashboard.html` | Multi-tenant enterprise view | **FUTURE** |
| `tenant/index.html` | Simplified tenant home | **DUPLICATE** |

**🔧 FIX:** Use `dashboard-v2.html` as main, archive others

---

### 📄 DOCUMENT MANAGEMENT (6 VERSIONS!)

| File | Purpose | Status |
|------|---------|--------|
| `documents.html` | Document intake (1254 lines) | **MAIN** |
| `documents-v2.html` | V2 version | **DUPLICATE** |
| `documents_simple.html` | Simplified version | **DUPLICATE** |
| `document_intake.html` | Upload-focused | **DUPLICATE** |
| `tenant/documents.html` | Tenant role version | **DUPLICATE** |
| `admin/document_intake.html` | Admin version | **SPECIALIZED** |

**🔧 FIX:** Consolidate to ONE `documents.html`

---

### 📅 TIMELINE PAGES (5 VERSIONS!)

| File | Purpose | Status |
|------|---------|--------|
| `timeline.html` | Main timeline | **MAIN** |
| `timeline-v2.html` | V2 with sidebar | **DUPLICATE** |
| `timeline-builder.html` | Manual event builder | **AUXILIARY** |
| `timeline_auto_build.html` | Auto-builder | **AUXILIARY** |
| `interactive-timeline.html` | Interactive version | **DUPLICATE** |
| `tenant/timeline.html` | Tenant role version | **DUPLICATE** |

**🔧 FIX:** Keep `timeline.html` + `timeline-builder.html` only

---

### 📆 CALENDAR (2 VERSIONS)

| File | Purpose | Status |
|------|---------|--------|
| `calendar.html` | Main calendar | **MAIN** |
| `calendar-v2.html` | V2 with sidebar | **DUPLICATE** |

**🔧 FIX:** Keep only `calendar.html`

---

### ⚖️ EVICTION DEFENSE WORKFLOW (CRITICAL PATH)

| File | Purpose | Status | Order |
|------|---------|--------|-------|
| `dakota_defense.html` | Defense hub | **CRITICAL** | 1 |
| `eviction_answer.html` | File answer form | **CRITICAL** | 2 |
| `counterclaim.html` | File counterclaim | **CRITICAL** | 3 |
| `motions.html` | File motions | **CRITICAL** | 4 |
| `hearing_prep.html` | Prepare for hearing | **CRITICAL** | 5 |
| `/zoom-court` | Zoom hearing guide | **CRITICAL** | 6 |
| `court_packet.html` | Generate court packet | **CRITICAL** | 7 |
| `court_learning.html` | Court procedures | **AUXILIARY** | - |

**✅ This is the CORE workflow - keep all!**

---

### 📚 LEGAL RESEARCH

| File | Purpose | Status |
|------|---------|--------|
| `law_library.html` | Browse MN statutes | **KEEP** |
| `legal_analysis.html` | AI analysis | **KEEP** |
| `legal_trails.html` | Research history | **KEEP** |
| `research.html` | Research center | **DUPLICATE** |
| `research_module.html` | Research module | **DUPLICATE** |

**🔧 FIX:** Merge research pages into `law_library.html`

---

### 💼 CASE MANAGEMENT

| File | Purpose | Status |
|------|---------|--------|
| `briefcase.html` | Document organizer | **KEEP** |
| `cases.html` | Case list | **KEEP** |
| `contacts.html` | Contact manager | **KEEP** |
| `journey.html` | User journey tracker | **DUPLICATE** |
| `my_tenancy.html` | Tenancy info | **KEEP** |

---

### 📝 FORM BUILDERS

| File | Purpose | Status |
|------|---------|--------|
| `letter_builder.html` | Generate letters | **KEEP** |
| `complaints.html` | File complaints | **KEEP** |
| `intake.html` | Complaint intake | **DUPLICATE** |
| `pdf_tools.html` | PDF manipulation | **AUXILIARY** |

---

### 🔐 ONBOARDING & ROLES (COMPLEX)

| File | Purpose | Status |
|------|---------|--------|
| `onboarding/welcome.html` | Onboarding start | **DUPLICATE** |
| `onboarding/select-role.html` | Role selection | **KEEP** |
| `onboarding/validate-advocate.html` | Advocate validation | **KEEP** |
| `onboarding/validate-legal.html` | Legal validation | **KEEP** |
| `setup_wizard.html` | Setup wizard | **DUPLICATE** |
| `storage_setup.html` | Cloud storage setup | **KEEP** |
| `roles.html` | Role management | **KEEP** |

---

### 👥 ROLE-SPECIFIC PORTALS

#### Tenant Portal (`/static/tenant/`)
| File | Purpose |
|------|---------|
| `index.html` | Tenant home |
| `documents.html` | Tenant docs |
| `timeline.html` | Tenant timeline |
| `help.html` | Tenant help |

#### Advocate Portal (`/static/advocate/`)
| File | Purpose |
|------|---------|
| `index.html` | Advocate home |
| `clients.html` | Client list |
| `intake.html` | Client intake |
| `queue.html` | Work queue |

#### Legal Portal (`/static/legal/`)
| File | Purpose |
|------|---------|
| `index.html` | Legal home |
| `cases.html` | Case management |
| `filings.html` | Court filings |
| `conflicts.html` | Conflict check |
| `privileged.html` | Privileged docs |

#### Admin Portal (`/static/admin/`)
| File | Purpose |
|------|---------|
| `mission_control.html` | Admin dashboard |
| `document_intake.html` | Bulk intake |

---

### 🧠 ADVANCED FEATURES

| File | Purpose | Status |
|------|---------|--------|
| `brain.html` | Positronic Brain visualization | **AUXILIARY** |
| `mesh_network.html` | P2P network status | **AUXILIARY** |
| `recognition.html` | Document recognition | **AUXILIARY** |
| `crawler.html` | Web crawler | **DEV TOOL** |
| `evaluation_report.html` | System evaluation | **DEV TOOL** |
| `module-converter.html` | Module converter | **DEV TOOL** |
| `layout_builder.html` | Layout builder | **DEV TOOL** |
| `style_editor.html` | Style editor | **DEV TOOL** |
| `page_editor.html` | Page editor | **DEV TOOL** |

---

### 📜 STATIC/INFO PAGES

| File | Purpose | Status |
|------|---------|--------|
| `about.html` | About page | **KEEP** |
| `privacy.html` | Privacy policy | **KEEP** |
| `help.html` | Help center | **KEEP** |
| `sample_certificate.html` | Certificate example | **AUXILIARY** |

---

### 💰 FUNDING/RESOURCES

| File | Purpose | Status |
|------|---------|--------|
| `hud_funding.html` | HUD funding guide | **KEEP** |
| `funding_search.html` | Search funding | **KEEP** |
| `fraud.html` | Fraud reporting | **KEEP** |
| `exposure.html` | Landlord exposure | **KEEP** |
| `campaign.html` | Advocacy campaigns | **AUXILIARY** |

---

### 🗂️ ARCHIVED (22 files in `_archive/`)

All files in `_archive/` should be deleted after verifying no active links.

---

## 🔀 API ROUTERS (55+ endpoints)

### Core Routes (Prefixes)
| Router | Prefix | Purpose |
|--------|--------|---------|
| dashboard | `/api/dashboard` | Dashboard data |
| documents | `/api/documents` | Document CRUD |
| briefcase | `/api/briefcase` | Folder/file organization |
| timeline | (via copilot) | Timeline events |
| calendar | (via copilot) | Calendar events |

### Eviction Defense
| Router | Prefix | Purpose |
|--------|--------|---------|
| eviction_defense | `/api/eviction-defense` | Defense workflow |
| court_forms | `/api/forms` | Court form generation |
| court_packet | `/api/court-packet` | Packet generation |
| zoom_court | `/api/zoom-court` | Zoom prep |
| zoom_court_prep | `/api/zoom-court` | Hearing prep |

### Legal Research
| Router | Prefix | Purpose |
|--------|--------|---------|
| law_library | `/api/law-library` | Statute search |
| legal_analysis | `/api/legal-analysis` | AI analysis |
| legal_trails | `/legal-trails` | Research history |
| research | `/api/research` | Research module |

### Intake & Setup
| Router | Prefix | Purpose |
|--------|--------|---------|
| intake | `/api/intake` | Document intake |
| guided_intake | `/api/guided-intake` | Wizard intake |
| setup | (via setup) | Initial setup |
| storage | `/storage` | Cloud storage OAuth |

### Advanced
| Router | Prefix | Purpose |
|--------|--------|---------|
| brain | (via brain) | Positronic brain |
| mesh_network | (via mesh_network) | P2P network |
| recognition | `/api/recognition` | Document recognition |
| extraction | `/api/extraction` | Form extraction |

---

## 🚶 USER JOURNEY ANALYSIS

### Current Flow (FRAGMENTED)
```
START
  │
  ├─→ index.html (Elbow UI)
  │     └─→ ??? (no clear next step)
  │
  ├─→ home.html 
  │     └─→ "Get Started" → ??? 
  │
  ├─→ welcome.html
  │     └─→ onboarding/welcome.html
  │           └─→ select-role.html
  │                 ├─→ Tenant → storage/providers
  │                 ├─→ Advocate → validate-advocate.html
  │                 └─→ Legal → validate-legal.html
  │
  ├─→ complete-journey.html
  │     └─→ Step-by-step onboarding (ORPHANED)
  │
  └─→ crisis_intake.html
        └─→ Emergency intake (ORPHANED)
```

### RECOMMENDED Flow (SIMPLIFIED)
```
START: index.html (Single Entry Point)
  │
  └─→ Role Selection (inline, not separate page)
        │
        ├─→ TENANT (Primary Flow)
        │     │
        │     └─→ dashboard-v2.html (Home)
        │           │
        │           ├─→ documents.html (Upload docs)
        │           │     └─→ recognition.html (if needed)
        │           │
        │           ├─→ timeline.html (Track events)
        │           │     └─→ timeline-builder.html
        │           │
        │           ├─→ calendar.html (Deadlines)
        │           │
        │           └─→ EVICTION DEFENSE (if facing eviction)
        │                 │
        │                 ├─→ dakota_defense.html (Hub)
        │                 ├─→ eviction_answer.html (Step 1)
        │                 ├─→ counterclaim.html (Step 2)
        │                 ├─→ motions.html (Step 3)
        │                 ├─→ hearing_prep.html (Step 4)
      │                 ├─→ /zoom-court (Step 5)
        │                 └─→ court_packet.html (Generate)
        │
        ├─→ ADVOCATE
        │     └─→ advocate/index.html
        │           ├─→ advocate/clients.html
        │           ├─→ advocate/queue.html
        │           └─→ advocate/intake.html
        │
        └─→ LEGAL
              └─→ legal/index.html
                    ├─→ legal/cases.html
                    └─→ legal/filings.html
```

---

## 🎯 PAGES BY CRITICALITY

### 🔴 CRITICAL (Core Workflow - Keep & Improve)
1. `index.html` (or `welcome.html`) - Entry point
2. `dashboard-v2.html` - Main hub
3. `documents.html` - Document management
4. `timeline.html` - Event tracking
5. `calendar.html` - Deadlines
6. `dakota_defense.html` - Defense hub
7. `eviction_answer.html` - File answer
8. `hearing_prep.html` - Prep for court
9. `court_packet.html` - Generate packet
10. `briefcase.html` - Organize for court

### 🟡 IMPORTANT (Supporting Features)
1. `law_library.html` - Legal research
2. `legal_analysis.html` - AI help
3. `letter_builder.html` - Generate letters
4. `complaints.html` - File complaints
5. `contacts.html` - Manage contacts
6. `storage_setup.html` - Cloud setup
7. `help.html` - Help center
8. Role portals (tenant/, advocate/, legal/)

### 🟢 AUXILIARY (Nice to Have)
1. `hud_funding.html` - Funding info
2. `fraud.html` - Fraud reporting
3. `exposure.html` - Landlord research
4. `brain.html` - AI visualization
5. `/zoom-court` - Zoom tips
6. `counterclaim.html` - Counterclaims
7. `motions.html` - Motions

### ⚪ REMOVABLE (Duplicates/Dev Tools)
1. All `-v2` versions (keep one)
2. All `_archive/` files
3. `home.html` - orphaned
4. `complete-journey.html` - duplicate
5. `crisis_intake.html` - orphaned
6. `index.html` ("Elbow" brand) - brand conflict
7. Dev tools (crawler, module-converter, etc.)

---

## 🔍 DEAD ENDS & BROKEN NAVIGATION

### Dead End Pages (No Clear Next Step)
1. `home.html` - Has "Get Started" but no destination
2. `index.html` - Different brand, no integration
3. `complete-journey.html` - Wizard ends nowhere
4. `sample_certificate.html` - Informational only
5. `evaluation_report.html` - Dev tool

### Broken Links Found
1. `tenant/index.html` → `/static/tenant/calendar.html` (doesn't exist)
2. `tenant/index.html` → `/static/tenant/copilot.html` (doesn't exist)
3. `tenant/index.html` → `/static/court_forms.html` (doesn't exist)
4. Various archive pages have broken links

### Navigation Inconsistencies
1. Some pages use shared-nav, others don't
2. Some pages have sidebar, others don't
3. Role portals have different nav structures
4. Dashboard vs Command Center confusion

---

## 📋 CONSOLIDATION RECOMMENDATIONS

### Phase 1: Immediate Cleanup
1. Delete all `_archive/` files
2. Choose ONE entry point (recommend `welcome.html`)
3. Remove `home.html`, `index.html` (Elbow), `complete-journey.html`
4. Remove all `-v2` versions except `dashboard-v2.html`

### Phase 2: Merge Duplicates
1. Merge all document pages → `documents.html`
2. Merge all timeline pages → `timeline.html` + `timeline-builder.html`
3. Merge research pages → `law_library.html`
4. Merge intake pages → single guided intake

### Phase 3: Simplify Roles
1. Make tenant flow the DEFAULT (no role selection needed)
2. Add "Professional Mode" toggle for advocate/legal
3. Remove separate role portals, use feature flags instead

### Phase 4: Navigation Overhaul
1. Implement consistent shared-nav across ALL pages
2. Add breadcrumbs for context
3. Add progress indicators for multi-step workflows
4. Add "Next Step" buttons at bottom of each page

---

## 📊 METRICS

| Category | Count | Should Be |
|----------|-------|-----------|
| Entry Points | 6 | 1 |
| Dashboard Versions | 4 | 1 |
| Document Pages | 6 | 1 |
| Timeline Pages | 5 | 2 |
| Total Active Pages | 83 | ~30 |
| API Routers | 55+ | ~30 |
| Role Portals | 4 | 1 (with modes) |

**Estimated Reduction: 60% of pages can be consolidated or removed**

---

## 🎬 SUGGESTED SIMPLIFIED ARCHITECTURE

```
static/
├── index.html          # Single entry, role selection
├── dashboard.html      # Main hub (merged from v2)
├── documents.html      # All document functions
├── timeline.html       # Event tracking
├── calendar.html       # Deadlines & scheduling
├── defense/            # Eviction defense workflow
│   ├── index.html      # Defense hub
│   ├── answer.html     # File answer
│   ├── prep.html       # Hearing prep
│   └── packet.html     # Court packet
├── legal/              # Legal tools
│   ├── library.html    # Law library + research
│   ├── analysis.html   # AI analysis
│   └── letters.html    # Letter builder
├── help/               # Help & resources
│   ├── index.html      # Help center
│   ├── privacy.html    # Privacy policy
│   └── about.html      # About
└── settings/           # Settings
    ├── index.html      # Settings hub
    └── storage.html    # Cloud storage
```

**From 105 files → ~20 files**
