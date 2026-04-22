# Semptify GUI Codemap
## Complete mapping of contracts, routes, templates, and static files

**Generated**: 2026-04-21
**Total Contracts**: 95
**Static HTML Pages**: 83
**Jinja2 Templates**: 29

---

## Navigation

- [Contract-to-GUI Mapping](#contract-to-gui-mapping)
- [Static HTML Inventory](#static-html-inventory)
- [Template Inventory](#template-inventory)
- [Router Inventory](#router-inventory)
- [Missing GUI Components](#missing-gui-components)

---

## Contract-to-GUI Mapping

### ✅ Fully Wired (Contract + Router + Static HTML)

| Contract ID | Route | Static HTML | Template | Status |
|-------------|-------|-------------|----------|--------|
| `welcome` | `/` | `welcome.html` | `pages/welcome.html` | ✅ |
| `dashboard` | `/dashboard` | `dashboard.html` | `pages/dashboard.html` | ✅ |
| `document_intake` | `/document-intake` | `document_intake.html` | - | ✅ |
| `vault` | `/vault` | `vault.html` | `pages/vault.html` | ✅ |
| `timeline` | `/timeline` | `timeline.html` | `pages/timeline.html` | ✅ |
| `calendar` | `/calendar` | `calendar.html` | - | ✅ |
| `eviction_answer` | `/eviction-answer` | `eviction_answer.html` | - | ✅ |
| `court_packet` | `/court-packet` | `court_packet.html` | - | ✅ |
| `hearing_prep` | `/hearing-prep` | `hearing_prep.html` | - | ✅ |
| `motions` | `/motions` | `motions.html` | - | ✅ |
| `counterclaim` | `/counterclaim` | `counterclaim.html` | - | ✅ |
| `legal_analysis` | `/legal-analysis` | `legal_analysis.html` | `pages/legal-analysis.html` | ✅ |
| `law_library` | `/law-library` | `law_library.html` | - | ✅ |
| `document_viewer` | `/document-viewer` | `document_viewer.html` | - | ✅ |
| `crisis_intake` | `/crisis-intake` | `crisis_intake.html` | - | ✅ |
| `settings` | `/settings` | `settings-v2.html` | - | ✅ |
| `storage_setup` | `/storage-setup` | `storage_setup.html` | - | ✅ |
| `help` | `/help` | `help.html` | - | ✅ |
| `contacts` | `/contacts` | `contacts.html` | - | ✅ |
| `correspondence` | `/correspondence` | `correspondence.html` | - | ✅ |
| `letter_builder` | `/letter-builder` | `letter_builder.html` | - | ✅ |
| `pdf_tools` | `/pdf-tools` | `pdf_tools.html` | - | ✅ |
| `briefcase` | `/briefcase` | `briefcase.html` | - | ✅ |
| `case_builder` | `/case-builder` | `cases.html` | - | ✅ |
| `dakota_defense` | `/dakota-defense` | `dakota_defense.html` | - | ✅ |
| `research` | `/research` | `research.html` | - | ✅ |

### 📬 Document Delivery System (2026-04-21)

| Contract ID | Route | Static HTML | Template | Status |
|-------------|-------|-------------|----------|--------|
| `document_signature` | `/delivery/sign` | `document_signer.html` | - | ✅ Fill & Sign |
| `document_delivery_inbox` | `/delivery/inbox` | `delivery_inbox.html` | - | ✅ List view |
| `document_delivery_send` | `/delivery/send` | `delivery_send.html` | - | ✅ Send with Communication |
| `document_rejection` | `/delivery/reject` | `document_signer.html` (reject modal) | - | ✅ Rejection with vault |

**API Endpoints:**
- `/api/delivery/send` - Send documents (Advocate, Legal, Admin, Manager)
- `/api/delivery/inbox` - List deliveries for tenant
- `/api/delivery/{id}/sign` - Sign document
- `/api/delivery/{id}/reject` - Reject document

**Storage:** All deliveries and rejections stored as overlays in vault

### 💬 Communication System (2026-04-21)

| Contract ID | Route | Static HTML | Template | Status |
|-------------|-------|-------------|----------|--------|
| `communications` | `/api/communications/*` | `document_signer.html` (chat panel) | - | ✅ |

**API Endpoints:**
- `/api/communications/conversations` - List/create conversations
- `/api/communications/conversations/{id}/messages` - Send messages
- `/api/communications/documents/{id}/fill-and-sign` - Sign with messaging
- `/api/communications/documents/{id}/reject` - Reject with vault record

**Features:**
- Direct messaging between tenant and all roles
- Document collaboration threads
- In-browser document filling and signing
- Signed/rejected documents saved to vault
- Real-time chat in document signer

**Storage:** Messages stored as COMMUNICATION overlays in `Semptify5.0/Vault/communications/`

### ✅ Recently Upgraded from Placeholder

| Contract ID | Route | Static HTML | Size | Status |
|-------------|-------|-------------|------|--------|
| `tenancy` | `/tenancy` | `my_tenancy.html` | ~15KB | ✅ Full tenancy dashboard |
| `zoom_court` | `/zoom-court` | `zoom_court.html` | ~12KB | ✅ Zoom prep with checklist |
| `journey` | `/journey` | `journey.html` | ~35KB | ✅ 4-phase tenant journey guide |
| `complete_journey` | `/complete-journey` | `complete-journey.html` | ~18KB | ✅ Post-case completion guide |
| `interactive_timeline` | `/interactive-timeline` | `interactive-timeline.html` | ~22KB | ✅ Visual timeline with filters |
| `timeline_builder` | `/timeline-builder` | `timeline-builder.html` | ~25KB | ✅ Manual timeline construction |

### ⚠️ Remaining Placeholder Pages

| Contract ID | Route | Static HTML | Size | Status |
|-------------|-------|-------------|------|--------|
| `document_calendar` | `/document-calendar` | `document_calendar.html` | 45KB | ✅ Verify |

### 📁 Directory-Based (Role Portals)

| Contract ID | Route | Directory | Status |
|-------------|-------|-----------|--------|
| `tenant` | `/tenant` | `static/tenant/` | ✅ |
| `advocate_portal` | `/advocate` | `static/advocate/` | ✅ |
| `manager_portal` | `/manager` | `static/manager/` | ✅ New - caseload dashboard |
| `admin_portal` | `/admin` | `static/admin/` | ✅ |
| `legal_portal` | `/legal` | `static/legal/` | ✅ |

### ✅ Recently Confirmed Wired

| Contract ID | Route | Static HTML | Status |
|-------------|-------|-------------|--------|
| `document_delivery_inbox` | `/delivery/inbox` | `delivery_inbox.html` | ✅ Wired to `/api/delivery/inbox` |
| `document_signature` | `/delivery/sign` | `document_signer.html` | ✅ Sign + view modes, linked from inbox |
| `document_delivery_send` | `/delivery/send` | `delivery_send.html` | ✅ Professional send flow with vault integration |
| `invite_advocate` | `/invite-advocate` | `invite-advocate.html` | ✅ Tenant invite page built |

### ❌ Missing GUI (No HTML Found)

| Contract ID | Route | Priority | Notes |
|-------------|-------|----------|-------|
| `storage_reconnect` | `/storage-reconnect` | Low | PARKED — awaiting identity format decision |

---

## Static HTML Inventory

### Primary Pages (Full Implementation)
```
static/
├── welcome.html              (34KB) - Landing page
├── dashboard.html            (94KB) - Main dashboard
├── document_intake.html      (197KB) - Document upload
├── vault.html                (64KB) - Document vault
├── timeline.html             (34KB) - Case chronology
├── calendar.html             (34KB) - Deadline tracking
├── eviction_answer.html      (39KB) - Form generation
├── court_packet.html         (26KB) - Court filing builder
├── hearing_prep.html         (21KB) - Hearing preparation
├── motions.html              (30KB) - Motion templates
├── counterclaim.html         (31KB) - Counterclaim builder
├── legal_analysis.html       (64KB) - Case analysis
├── law_library.html          (54KB) - Legal resources
├── document_viewer.html      (64KB) - Document preview
├── crisis_intake.html        (32KB) - Emergency triage
├── settings-v2.html          (35KB) - User settings
├── storage_setup.html        (46KB) - OAuth connection
├── help.html                 (39KB) - Help center
├── contacts.html             (52KB) - Contact management
├── correspondence.html       (41KB) - Communications
├── letter_builder.html       (17KB) - Letter drafting
├── pdf_tools.html            (65KB) - PDF utilities
├── briefcase.html            (109KB) - Document organizer
├── cases.html                (69KB) - Case management
├── dakota_defense.html       (34KB) - Eviction defense
├── research.html             (22KB) - Legal research
├── home.html                 (22KB) - Post-login home
└── index.html                (11KB) - Entry point
```

### Subsystem Pages
```
static/
├── brain.html                (29KB) - Brain interface
├── command_center.html       (79KB) - Admin operations
├── complaints.html           (88KB) - Complaint filing
├── campaign.html             (51KB) - Campaign tools
├── court_learning.html       (33KB) - Court education
├── crawler.html              (25KB) - Web crawler
├── crawler_control.html      (51KB) - Crawler admin
├── document-converter.html   (29KB) - Format conversion
├── evaluation_report.html    (44KB) - System reports
├── exposure.html             (23KB) - Fraud exposure
├── focus.html                (18KB) - Focus mode
├── fraud.html                (19KB) - Fraud detection
├── funding_search.html       (44KB) - HUD funding
├── hud_funding.html          (27KB) - Funding details
├── layout_builder.html       (55KB) - UI builder
├── legal_trails.html         (61KB) - Legal trails
├── mesh_network.html         (23KB) - Mesh tools
├── module-converter.html     (44KB) - Module tools
├── motions.html              (30KB) - Motion builder
├── page_editor.html          (31KB) - Page editor
├── page-index.html           (55KB) - Page directory
├── recognition.html          (61KB) - Recognition sys
├── research_module.html      (51KB) - Research tools
├── roles.html                (54KB) - Role selection
├── setup_wizard.html         (65KB) - Setup flow
├── style_editor.html         (28KB) - CSS editor
└── sidebar_with_auto_mode.html (13KB) - Auto mode UI
```

### Placeholder Pages (Need Content)
```
static/
├── my_tenancy.html           (622b) ⚠️
├── journey.html              (622b) ⚠️
├── complete-journey.html     (622b) ⚠️
├── interactive-timeline.html (622b) ⚠️
├── timeline-builder.html     (622b) ⚠️
├── zoom_court.html           (856b) ⚠️
├── case.html                 (846b) ⚠️
├── timeline-v2.html          (622b) ⚠️
├── dashboard-v2.html         (584b) ⚠️
├── documents-v2.html         (684b) ⚠️
├── documents.html            (684b) ⚠️
├── documents_simple.html     (684b) ⚠️
├── enterprise-dashboard.html (584b) ⚠️
├── journey.html              (622b) ⚠️
├── my_tenancy.html           (622b) ⚠️
├── timeline.html             (622b) ⚠️
└── timeline_auto_build.html  (2.5KB) ⚠️
```

---

## Template Inventory

### Core Templates
```
app/templates/
├── base.html                           - Base layout
├── components/
│   ├── document_card.html              - Document display
│   └── upload_zone.html                - Upload component
├── legal/
│   ├── advocate_dashboard.html         - Advocate UI
│   └── housing_manager_monitor.html    - Manager monitor
├── pages/
│   ├── admin.html                      - Admin portal
│   ├── advocate.html                   - Advocate page
│   ├── auto_analysis_summary.html      - Analysis UI
│   ├── auto_mode_demo.html             - Demo page
│   ├── auto_mode_panel.html            - Auto mode UI
│   ├── batch_analysis_results.html     - Batch results
│   ├── dashboard.html                  - Dashboard template
│   ├── documents.html                  - Documents list
│   ├── error.html                      - Error page
│   ├── functionx.html                  - FunctionX UI
│   ├── gui_navigation_hub.html         - Navigation
│   ├── legal-analysis.html             - Analysis page
│   ├── legal.html                      - Legal portal
│   ├── mode_selector.html              - Mode selection
│   ├── onboarding-simple.html          - Onboarding
│   ├── register.html                   - Registration
│   ├── register_success.html           - Success page
│   ├── tenancy.html                    - Tenancy view
│   ├── tenant.html                     - Tenant portal
│   ├── tenant_dashboard.html           - Tenant dash
│   ├── timeline.html                   - Timeline view
│   ├── vault.html                      - Vault template
│   └── welcome.html                    - Welcome page
└── partials/
    └── workspace_stage_panel.html      - Stage panel
```

---

## Router Inventory

### Core Routers (83 files)
```
app/routers/
├── actions.py                  - Action endpoints
├── brain.py                   - Brain interface
├── briefcase.py               - Briefcase ops
├── calendar.py                - Calendar API
├── case_builder.py            - Case building
├── cloud_sync.py              - Cloud storage
├── complaints.py              - Complaints
├── contacts.py                - Contacts
├── context_loop.py            - Context system
├── court_forms.py             - Form generation
├── court_packet.py            - Court packets
├── crawler.py                 - Web crawler
├── documents.py               - Documents
├── emotion.py                 - Emotion tracking
├── enterprise_dashboard.py    - Enterprise
├── eviction/
│   ├── case.py                - Eviction cases
│   ├── flows.py               - Eviction flows
│   ├── forms.py               - Eviction forms
│   ├── learning.py            - Court learning
│   └── procedures.py          - Procedures
├── eviction_defense.py        - Defense tools
├── form_data.py               - Form data
├── fraud_exposure.py          - Fraud detection
├── free_api.py                - Free APIs
├── funding_search.py          - Funding
├── health.py                  - Health checks
├── hud_funding.py             - HUD funding
├── intake.py                  - Document intake
├── law_library.py             - Law library
├── legal_analysis.py          - Analysis
├── legal_trails.py            - Legal trails
├── location.py                - Location
├── mesh.py                    - Mesh network
├── module_hub.py              - Module system
├── overlays.py                - Overlay API
├── pdf_tools.py               - PDF tools
├── positronic_mesh.py         - Positronic
├── progress.py                - Progress
├── public_exposure.py         - Public exposure
├── registry.py                - Registry
├── research.py                - Research
├── security.py                - Security
├── setup.py                   - Setup
├── storage.py                 - Storage
├── tenancy_hub.py             - Tenancy
├── testing.py                 - Testing
├── timeline.py                - Timeline
├── vault.py                   - Vault
├── vault_all_in_one.py        - All-in-one
└── workflow.py                - Workflow
```

---

## Missing GUI Components

### Priority: Medium (New Contracts)

#### 1. Document Delivery Inbox (`/delivery/inbox`)
**Contract**: `CONTRACT_DOCUMENT_DELIVERY_INBOX`
**Purpose**: Tenant receives PENDING documents from advocates
**Needed**:
- `static/delivery_inbox.html` or `app/templates/pages/delivery_inbox.html`
- Router endpoint in `app/routers/delivery.py`
- List PENDING items from vault
- Show sender identity, timestamp, delivery type
- Accept/Reject buttons
- Link to signature flow

#### 2. Document Delivery Send (`/delivery/send`)
**Contract**: `CONTRACT_DOCUMENT_DELIVERY_SEND`
**Purpose**: Advocates send documents to tenants
**Needed**:
- `static/delivery_send.html` or template
- Router endpoint
- Document selection from vault
- Tenant recipient selection
- Delivery type toggle (review/sign)
- Read receipt checkbox
- Send button

#### 3. Document Signature (`/delivery/sign`)
**Contract**: `CONTRACT_DOCUMENT_SIGNATURE`
**Purpose**: Tenant signs received documents
**Needed**:
- `static/delivery_sign.html` or template
- Router endpoint
- Document preview
- Signature capture (browser native)
- Reject option with reason
- Save to vault on completion

### Priority: Low

#### 4. Storage Reconnect (`/storage-reconnect`)
**Contract**: `CONTRACT_STORAGE_RECONNECT`
**Purpose**: OAuth token recovery
**Status**: PARKED - awaiting identity format decision
**Notes**: May not need GUI if automated

---

## Wiring Patterns

### Pattern A: Static HTML Only
```python
# app/routers/my_page.py
@router.get("/my-page")
async def my_page():
    return FileResponse("static/my_page.html")
```

### Pattern B: Jinja2 Template
```python
# app/routers/my_page.py
@router.get("/my-page")
async def my_page(request: Request):
    return templates.TemplateResponse(
        "pages/my_page.html",
        {"request": request, "data": ...}
    )
```

### Pattern C: Template + Static Fallback
```python
@router.get("/my-page")
async def my_page(request: Request):
    if template_exists("pages/my_page.html"):
        return templates.TemplateResponse(...)
    return FileResponse("static/my_page.html")
```

---

## Statistics

| Category | Count | Complete | Placeholder | Missing |
|----------|-------|----------|-------------|---------|
| **Contracts** | 95 | 73 | 11 | 1 |
| **Static HTML** | 83 | 67 | 14 | 2 |
| **Templates** | 29 | 29 | 0 | 0 |
| **Routers** | 83 | 83 | 0 | 0 |

**GUI Coverage**: 78% (73/93 wired)
**Placeholder Rate**: 15% (14 pages)

---

## Recommended Priority

1. **Document Delivery Send** - Medium priority, completes delivery flow — only remaining missing GUI
2. **Replace Placeholders** - Low priority, improve UX
3. **Storage Reconnect** - PARKED — await identity format decision
