# Page Customization Component Library

**Purpose:** Complete catalog of all objects, functions, modules & components for page assembly  
**Status:** Reference Only - For Planning Custom Page Layouts

---

## Part 1: Jinja2 UI Macros (Building Blocks)

**File:** `app/templates/components/ui_macros.html`

### 1.1 Layout Macros

| Macro | Purpose | Arguments | CSS Class |
| ------- | --------- | ----------- | ----------- |
| `hero(icon, title, desc, color)` | Page header with gradient | icon, title, desc, color="blue" | .ui-hero |
| `section_title(icon, text)` | Section divider | icon, text | .ui-section-title |
| `card_grid(min_width)` | Responsive grid container | min_width="280px" | .ui-card-grid |
| `quick_grid()` | Quick links grid | none | .ui-quick-grid |
| `info_box(type)` | Callout container | type="info" | .ui-infobox |
| `nav_bar(active)` | 5-link navigation | active="" | nav links |
| `ui_styles()` | Inline CSS for all macros | none | <style> |

### 1.2 Content Macros

| Macro | Purpose | Arguments | Example |
| ------- | --------- | ----------- | --------- |
| `service_card(href, icon, title, desc, featured, badge)` | Feature card | href, icon, title, desc, featured=false, badge="" | Link to /documents |
| `quick_link(href, icon, text)` | Small nav pill | href, icon, text | Quick task links |
| `vault_cta(title, desc, button_text)` | Upload prompt | defaults provided | Vault Door CTA |
| `emergency_box(title, desc, button_text, button_href)` | Urgent callout | title, desc, button params | Crisis help |
| `progress_widget(steps, current)` | Step indicator | steps=[], current=0 | Onboarding flow |
| `privacy_note()` | Privacy reminder | none | Standard text |

### 1.3 Color Options

Hero colors: `blue`, `purple`, `green`, `red`, `amber`  
Info box types: `info`, `warning`, `success`, `error`

---

## Part 2: Design System Function Groups

**Location:** `design-system/components/function-groups/`

### 2.1 Capture Functions (Document Intake)

| Component | File | Purpose | Size |
| ----------- | ------ | --------- | ------ |
| Upload Zone | `capture/upload-zone.html` | Drag-drop file upload | 8.3KB |
| Voice Intake | `capture/voice-intake.html` | Audio recording interface | 12.6KB |
| Quick Input | `capture/quick-input.html` | Fast text entry | 8.9KB |
| Demo | `capture/demo.html` | Showcase component | 5.5KB |

**CSS:** `capture/index.css`, `upload-zone.css`, `voice-intake.css`, `quick-input.css`

### 2.2 Understand Functions (Analysis)

| Component | File | Purpose | Size |
| ----------- | ------ | --------- | ------ |
| Timeline View | `understand/timeline-view.html` | Chronological display | View component |
| Risk Detection | `understand/risk-detection.html` | Risk analysis UI | Analysis view |
| Rights Analysis | `understand/rights-analysis.html` | Rights breakdown | Legal analysis |

**CSS:** `understand/index.css`, component-specific CSS

### 2.3 Plan Functions (Action Planning)

| Component | File | Purpose | Size |
| ----------- | ------ | --------- | ------ |
| Next Step Card | `plan/next-step-card.html` | Action prompt | Card component |
| Deadline Tracker | `plan/deadline-tracker.html` | Due date display | Tracker widget |
| Action List | `plan/action-list.html` | Task checklist | List component |

**CSS:** `plan/index.css`, `next-step-card.css`, `deadline-tracker.css`, `action-list.css`

### 2.4 Vault Functions (Storage)

| Component | File | Purpose | Size |
| ----------- | ------ | --------- | ------ |
| Vault Sidebar | `vault/vault-sidebar.html` | Persistent vault panel | Sidebar |
| Vault Sidebar Fixed | `vault/vault-sidebar-fixed.html` | Fixed position variant | Sidebar |
| Vault Sidebar Clean | `vault/vault-sidebar-clean.html` | Minimal version | Sidebar |

### 2.5 Role-Specific Dashboards

| Role | Component | File | Purpose |
| ------ | ----------- | ------ | --------- |
| Tenant | Emergency Actions | `role-specific/tenant/emergency-actions.html` | Crisis buttons |
| Tenant | Dashboard | `role-specific/tenant/dashboard.html` | Main tenant UI |
| Tenant | Case Summary | `role-specific/tenant/case-summary.html` | Case overview |
| Advocate | Dashboard | `role-specific/advocate/dashboard.html` | Advocate UI |
| Advocate | Client Management | `role-specific/advocate/client-management.html` | Client list |
| Legal | Dashboard | `role-specific/legal/dashboard.html` | Attorney UI |
| Admin | Dashboard | `role-specific/admin/dashboard.html` | Admin panel |

### 2.6 Onboarding Components

| Component | File | Purpose |
| ----------- | ------ | --------- |
| Welcome | `onboarding/welcome.html` | Entry component |
| Onboarding Tracker | `onboarding/onboarding-tracker.html` | Progress indicator |
| Demo | `onboarding/demo.html` | Interactive demo |

---

## Part 3: Static HTML Components (Reusable Includes)

**Location:** `static/components/`

| Component | File | Purpose | Size |
| ----------- | ------ | --------- | ------ |
| Footer | `footer.html` | Standard footer | 2.1KB |
| Header | `header.html` | Page header | 1.3KB |
| Interactive Timeline | `interactive-timeline.html` | Timeline widget | 21.8KB |
| Loading Overlay | `loading-overlay.html` | Spinner modal | 3.5KB |
| Main Navigation | `main-navigation.html` | Nav bar | 5.0KB |
| Preview Modal | `preview-modal.html` | Document preview | 11.9KB |
| Unified Footer | `unified-footer.html` | Dynamic footer | 5.0KB |
| Vault Button | `vault-button.html` | Upload trigger | 3.3KB |
| Vault Portal | `vault-portal.html` | Full vault UI | 8.8KB |

---

## Part 4: JavaScript Core Functions

**Location:** `static/js/core/`

### 4.1 App.js Functions

| Function | Purpose | File |
| ---------- | --------- | ------ |
| `initializeApp()` | App bootstrap | app.js |
| `setupEventListeners()` | Bind handlers | app.js |
| `handleNavigation()` | Nav logic | app.js |
| `showNotification()` | Toast messages | app.js |
| `fetchWithAuth()` | API wrapper | app.js |

### 4.2 Vault Portal Functions

| Function | Purpose | File |
| ---------- | --------- | ------ |
| `openVaultUpload()` | Trigger upload | vault-portal.js |
| `closeVaultPortal()` | Close modal | vault-portal.js |
| `handleFileSelect()` | File processing | vault-portal.js |
| `uploadToVault()` | Upload logic | vault-portal.js |
| `showVaultStatus()` | Status display | vault-portal.js |

### 4.3 WebSocket Client Functions

| Function | Purpose | File |
| ---------- | --------- | ------ |
| `connectWebSocket()` | WS connection | websocket-client.js |
| `handleMessage()` | Message handler | websocket-client.js |
| `sendMessage()` | Emit message | websocket-client.js |
| `subscribe()` | Channel join | websocket-client.js |

### 4.4 Other JS Files

| File | Functions | Purpose |
| ------ | ----------- | --------- |
| `location-detect.js` | Geolocation, timezone | Location services |
| `unified-footer-loader.js` | Footer injection | Dynamic footer |
| `workspace-stage-model.js` | Stage management | Workspace state |

---

## Part 5: Backend Modules (Python Functions)

**Location:** `app/modules/`

### 5.1 Document-Related Modules

| Module | Key Functions | Router | Purpose |
| -------- | --------------- | -------- | --------- |
| `documents` | upload, list, delete | Yes | Document management |
| `vault` | create_folders, health_check | Yes | Vault operations |
| `vault_engine` | process_document, index | Yes | Document processing |
| `document_delivery` | send, track, inbox | Yes | Document sharing |
| `document_converter` | convert_pdf, extract | No | Format conversion |
| `extraction` | extract_text, parse | Yes | Data extraction |

### 5.2 Case/Timeline Modules

| Module | Key Functions | Router | Purpose |
| -------- | --------------- | -------- | --------- |
| `case_builder` | build_case, analyze | Yes | Case assembly |
| `timeline` | add_event, view | Yes | Timeline management |
| `tenant_defense` | generate_response, analyze | No | Defense tools |
| `eviction_defense` | answer_generator, motions | Yes | Legal defense |
| `litigation_intelligence` | analyze, report | Yes | Case analysis |

### 5.3 Communication Modules

| Module | Key Functions | Router | Purpose |
| -------- | --------------- | -------- | --------- |
| `communication` | send_message, inbox | Yes | Messaging |
| `contacts` | manage, import | Yes | Contact book |
| `calendar` | events, reminders | Yes | Scheduling |
| `zoom_court` | join, prepare | Yes | Court video |

### 5.4 Research & Analysis Modules

| Module | Key Functions | Router | Purpose |
| -------- | --------------- | -------- | --------- |
| `research` | search, summarize | Yes | Legal research |
| `research_module` | deep_analysis, dossier | No | Advanced research |
| `law_library` | lookup, cite | Yes | Law reference |
| `legal_analysis` | analyze_document | Yes | Doc analysis |
| `legal_trails` | track_precedent | Yes | Case tracking |
| `state_laws` | get_state_info | Yes | State law data |

### 5.5 Intake & Forms Modules

| Module | Key Functions | Router | Purpose |
| -------- | --------------- | -------- | --------- |
| `intake` | process_intake, guide | Yes | User onboarding |
| `guided_intake` | step_by_step | Yes | Wizard flow |
| `complaint_wizard_module` | generate_complaint | No | Complaint builder |
| `court_forms` | fill_form, generate | Yes | Form completion |
| `public_forms` | access_form | Yes | Public forms |

### 5.6 Administrative Modules

| Module | Key Functions | Router | Purpose |
| -------- | --------------- | -------- | --------- |
| `admin` | manage_users, settings | Yes | Admin panel |
| `dashboard` | get_stats, widgets | Yes | Dashboard data |
| `enterprise_dashboard` | org_analytics | Yes | Org dashboard |
| `manager_dashboard` | property_mgmt | Yes | Manager tools |
| `page_editor` | edit_content | Yes | CMS functions |
| `page_index` | list_pages, search | Yes | Page registry |

### 5.7 AI/Auto Modules

| Module | Key Functions | Router | Purpose |
| -------- | --------------- | -------- | --------- |
| `auto_mode` | auto_analyze, suggest | Yes | Auto analysis |
| `brain` | process_query | Yes | AI engine |
| `context_loop` | maintain_context | Yes | Context tracking |
| `recognition` | recognize_doc_type | Yes | Doc recognition |
| `overlays` | create_overlay | Yes | Metadata layer |

---

## Part 6: Page Templates (Structural Options)

### 6.1 Full Page Templates (Jinja2)

**Location:** `app/templates/pages/`

| Template | Extends | Key Features | Use Case |
| ---------- | --------- | -------------- | ---------- |
| `base.html` | None (root) | Full layout, nav, footer | All pages |
| `welcome.html` | base.html | Role selection, onboarding | Entry point |
| `library.html` | base.html | Hero, cards, resources | Resource hub |
| `office.html` | base.html | Services grid, quick tasks | Case mgmt |
| `documents.html` | base.html | Upload zone, doc list | Vault view |
| `tools.html` | base.html | Tool grid | Utilities |
| `help.html` | base.html | Help topics, search | Support |
| `timeline.html` | base.html | Timeline view | Journal |
| `vault.html` | standalone | Full vault UI | Document mgmt |

### 6.2 Role Dashboards

| Template | Role | Extends | Key Components |
| ---------- | ------ | --------- | ---------------- |
| `tenant_home.html` | Tenant | base.html | Quick access, stats |
| `tenant_dashboard.html` | Tenant | standalone | Full dashboard |
| `tenant_journal.html` | Tenant | standalone | Journal interface |
| `tenant_inbox.html` | Tenant | standalone | Communications |
| `tenant_capture.html` | Tenant | standalone | Document capture |
| `tenant_help.html` | Tenant | standalone | Contextual help |
| `advocate.html` | Advocate | base.html | Client mgmt |
| `legal.html` | Legal | base.html | Case tools |
| `admin.html` | Admin | base.html | System mgmt |
| `manager_dashboard.html` | Manager | standalone | Property tools |

---

## Part 7: Static Page Archive (Legacy Ideas)

**Location:** `staticbac/` (100+ files, NOT for production)

### 7.1 Notable Legacy Pages (Ideas to Salvage)

| File | Size | Features Worth Migrating |
| ------ | ------ | -------------------------- |
| `briefcase.html` | 108KB | 14-color highlighter system |
| `command_center.html` | 79KB | Command palette UI |
| `complaints.html` | 88KB | Complaint builder workflow |
| `law_library.html` | 54KB | Citation formatting |
| `legal_analysis.html` | 64KB | Analysis dashboard layout |
| `document_viewer.html` | 64KB | PDF viewer with annotations |
| `letter_builder.html` | 17KB | Letter template system |
| `calendar.html` | 34KB | Full calendar integration |
| `case.html` / `cases.html` | 69KB | Case management interface |
| `crawler.html` | 25KB | Document crawler UI |
| `mesh_network.html` | 23KB | Network visualization |
| `page_editor.html` | 31KB | WYSIWYG editor |
| `layout_builder.html` | 55KB | Drag-drop layout tool |
| `brain.html` | 29KB | AI interface patterns |
| `focus.html` | 18KB | Distraction-free mode |
| `hearing_prep.html` | 21KB | Court preparation checklist |
| `motions.html` | 30KB | Motion template library |
| `correspondence.html` | 41KB | Letter management |

### 7.2 Archive Subfolders

| Folder | Contents |
| -------- | ---------- |
| `_archive/dashboards/` | 3 dashboard variants |
| `_archive/documents/` | 4 document UI versions |
| `_archive/timelines/` | 5 timeline implementations |
| `admin/` | 10 admin tools |
| `advocate/` | 3 advocate pages |
| `legal/` | Legal professional tools |
| `manager/` | Property manager tools |
| `tenant/` | Tenant-specific pages |

---

## Part 8: Assembly Guide (How to Build a Page)

### 8.1 Basic Page Structure

```jinja2
{% extends "base.html" %}
{% from "components/ui_macros.html" import hero, section_title, service_card, 
                                         card_grid, quick_link, quick_grid, 
                                         vault_cta, privacy_note, nav_bar, ui_styles %}

{% block title %}Your Page - Semptify{% endblock %}
{% block nav %}{{ nav_bar("active_tab") }}{% endblock %}

{% block styles %}{{ ui_styles() }}
<!-- Additional CSS -->
{% endblock %}

{% block content %}
{{ hero("🎨", "Page Title", "Description here", "blue") }}

{{ section_title("📁", "Section Name") }}
{% call card_grid() %}
    {{ service_card("/path", "🔧", "Feature Name", "Description", featured=true) }}
    <!-- More cards -->
{% endcall %}

{{ vault_cta() }}
{{ privacy_note() }}
{% endblock %}

{% block scripts %}
<!-- Page-specific JS -->
{% endblock %}
```text

### 8.2 Adding Design System Components

```jinja2
{# Include function group component #}
{% include "design-system/components/function-groups/capture/upload-zone.html" %}

{# Include with context #}
{% include "design-system/components/function-groups/vault/vault-sidebar-clean.html" %}

{# Role-specific component #}
{% include "design-system/components/function-groups/role-specific/tenant/emergency-actions.html" %}
```

### 8.3 Adding Static Components

```jinja2
{# HTML component include #}
{% include "static/components/vault-portal.html" %}

{# Or use the JS loader #}
<script src="/js/core/vault-portal.js"></script>
```text

### 8.4 Using Backend Module Data

```python
## In your router
from app.modules.documents import router as documents_router
from app.modules.timeline import router as timeline_router

## Get data for template
documents = await documents_router.get_documents(user_id)
timeline_events = await timeline_router.get_timeline(user_id)

return templates.TemplateResponse("page.html", {
    "request": request,
    "documents": documents,
    "timeline": timeline_events,
})
```

---

## Part 9: Customization Decision Matrix

### 9.1 Choosing Components by Page Type

| Page Type | Required | Optional Add-ons |
| ----------- | ---------- | ------------------ |
| Landing | hero, nav_bar | vault_cta, privacy_note |
| Dashboard | hero, card_grid, quick_grid | role-specific components |
| Document | upload-zone (capture) | vault sidebar |
| Timeline | timeline-view (understand) | deadline-tracker (plan) |
| Help | section_title, info_box | quick_link grid |
| Legal | rights-analysis | case-summary, next-step-card |
| Admin | dashboard widgets | admin components |

### 9.2 Choosing Functions by User Goal

| User Goal | Backend Module | Frontend Component |
| ----------- | ---------------- | ------------------- |
| Upload docs | documents, vault | upload-zone, vault-sidebar |
| Track case | timeline, case_builder | timeline-view, case-summary |
| Get help | tenant_help, communication | emergency-actions, inbox |
| Research | research, law_library | rights-analysis |
| Prepare filing | legal_filing, court_forms | document_viewer, letter_builder |
| Analyze risk | auto_mode, legal_analysis | risk-detection |

---

## Part 10: Complete Component Index

### 10.1 All HTML Files (Consolidated Count)

| Location | Count | Type |
| ---------- | ------- | ------ |
| `app/templates/pages/` | 25 | Jinja2 full pages |
| `app/templates/components/` | 4 | Jinja2 partials |
| `design-system/components/` | 25 | Function group components |
| `static/components/` | 9 | Static partials |
| `static/` (root pages) | 19 | Static full pages |
| `static/tenant/` | 7 | Tenant-specific |
| `static/onboarding/` | 6 | Onboarding flow |
| `static/public/` | 8 | Public marketing |
| `static/office/` | 4 | Office sub-pages |
| `static/mndes/` | 2 | Court compliance |
| `static/reconnect/` | 1 | Reconnect flow |
| `staticbac/` (archive) | 100+ | Legacy/backup |

**Total:** 200+ HTML files

### 10.2 All CSS Files

| Location | Count | Purpose |
| ---------- | ------- | --------- |
| `design-system/tokens/` | 7 | Design tokens |
| `design-system/components/` | 15 | Component styles |
| `design-system/patterns/` | 1 | Layout patterns |
| `static/css/components/` | 3 | Static component CSS |
| `staticbac/css/` | 1 | Legacy styles |

**Total:** 27 CSS files

### 10.3 All JS Files (Project)

| Location | Count | Purpose |
| ---------- | ------- | --------- |
| `static/js/core/` | 3 | Core functionality |
| `design-system/` | 2 | Design system JS |
| `static/js/` | 3 | Utilities |

**Total:** 8 JS files (excluding node_modules)

### 10.4 Python Modules with Routers

| Count | Modules |
| ------- | --------- |
| 90+ | `app/modules/*/` with routers |
| 25 | Core feature modules |
| 15 | Supporting modules |

---

## Appendix: File Trees for Reference

### A.1 Design System Structure

```text
design-system/
├── tokens/ (7 CSS files)
├── components/
│   ├── buttons.css, cards.css, forms.css
│   ├── toasts.css, modals.css, loading.css
│   ├── navigation.css
│   └── function-groups/
│       ├── capture/ (4 HTML, 4 CSS)
│       ├── understand/ (3 HTML, 4 CSS)
│       ├── plan/ (3 HTML, 3 CSS)
│       ├── vault/ (3 HTML)
│       ├── role-specific/ (6 HTML, 3 CSS)
│       └── onboarding/ (3 HTML)
├── layouts/
├── pages/
└── patterns/
```

### A.2 Template Structure

```text
app/templates/
├── base.html (canonical)
├── pages/ (25 Jinja2 templates)
│   ├── welcome.html
│   ├── library.html, office.html, tools.html, help.html
│   ├── documents.html, timeline.html, vault.html
│   ├── tenant_*.html (6 files)
│   ├── advocate.html, legal.html, admin.html
│   └── [other role pages]
└── components/
    ├── ui_macros.html (10 macros)
    ├── upload_zone.html
    ├── document_card.html
    └── functions_bar.html
```

### A.3 Static Archive Structure (For Reference)

```text
staticbac/
├── [root pages] (50+ files)
├── _archive/
│   ├── dashboards/
│   ├── documents/
│   └── timelines/
├── admin/ (10 files)
├── advocate/
├── components/
├── legal/
├── manager/
└── tenant/
```

---

#### END OF COMPONENT LIBRARY

*This is a complete reference for planning page customization. No implementation changes have been made.*
