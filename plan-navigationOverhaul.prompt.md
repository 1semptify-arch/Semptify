# Navigation & Workflow Overhaul Plan

**Goal:** Create a unified, logical user experience with clear progression from first visit through case resolution.

---

## Current Problems

1. **73 HTML pages** but only ~25 have shared navigation
2. **No clear first-visit flow** - users land on random pages
3. **No home page** for returning users
4. **Functions scattered** across pages without logical order
5. **Too many clicks** to accomplish tasks

---

## Proposed Structure

### 1. Entry Points (2 pages)

| Page | Purpose | When Shown |
|------|---------|------------|
| `welcome.html` | First-time user onboarding | No session/first visit |
| `home.html` | Returning user dashboard | Has active case |

### 2. Core Workflow Stages (Linear Progression)

```
STAGE 1: SETUP (First Visit)
├── Welcome → Choose situation
├── Intake → Enter basic info
└── Storage Setup → Connect cloud (optional)

STAGE 2: DOCUMENT COLLECTION
├── Upload documents (lease, notices, receipts)
├── AI extracts dates, parties, amounts
└── Auto-builds timeline

STAGE 3: CASE BUILDING
├── Review extracted data
├── Build legal arguments
└── Prepare court documents

STAGE 4: COURT PREP
├── Generate answer/counterclaim
├── Create court packet
└── Zoom court prep

STAGE 5: ONGOING
├── Calendar/deadlines
├── Communication tracking
└── Case updates
```

### 3. Simplified Navigation (7 main sections)

```javascript
sections: [
    {
        id: 'home',
        title: '🏠 Home',
        items: [
            { icon: '🏠', label: 'Dashboard', href: '/static/home.html' },
            { icon: '📊', label: 'Case Status', href: '/static/case.html' },
        ]
    },
    {
        id: 'intake',
        title: '📥 Step 1: Intake',
        items: [
            { icon: '📋', label: 'Document Upload', href: '/static/document_intake.html' },
            { icon: '🔍', label: 'AI Recognition', href: '/static/recognition.html' },
            { icon: '💼', label: 'Briefcase', href: '/static/briefcase.html' },
        ]
    },
    {
        id: 'timeline',
        title: '📅 Step 2: Timeline',
        items: [
            { icon: '⚡', label: 'Auto-Build', href: '/static/timeline_auto_build.html' },
            { icon: '📅', label: 'View Timeline', href: '/static/timeline.html' },
            { icon: '📆', label: 'Calendar', href: '/static/calendar.html' },
        ]
    },
    {
        id: 'defense',
        title: '⚖️ Step 3: Defense',
        items: [
            { icon: '📖', label: 'Law Library', href: '/static/law_library.html' },
            { icon: '📝', label: 'File Answer', href: '/static/eviction_answer.html' },
            { icon: '⚔️', label: 'Counterclaim', href: '/static/counterclaim.html' },
            { icon: '📋', label: 'Motions', href: '/static/motions.html' },
        ]
    },
    {
        id: 'court',
        title: '🏛️ Step 4: Court',
        items: [
            { icon: '📦', label: 'Court Packet', href: '/static/court_packet.html' },
            { icon: '🎯', label: 'Hearing Prep', href: '/static/hearing_prep.html' },
            { icon: '💻', label: 'Zoom Court', href: '/static/zoom_court.html' },
        ]
    },
    {
        id: 'tools',
        title: '🔧 Tools',
        items: [
            { icon: '✉️', label: 'Letters', href: '/static/letter_builder.html' },
            { icon: '📝', label: 'Complaints', href: '/static/complaints.html' },
            { icon: '📇', label: 'Contacts', href: '/static/contacts.html' },
            { icon: '📬', label: 'Correspondence', href: '/static/correspondence.html' },
        ]
    },
    {
        id: 'vault',
        title: '📁 Vault',
        items: [
            { icon: '🔐', label: 'Document Vault', href: '/static/vault.html' },
            { icon: '📑', label: 'PDF Tools', href: '/static/pdf_tools.html' },
        ]
    },
]
```

### 4. Pages to Keep vs. Consolidate

**KEEP (Core Pages - 20)**
- home.html (new - returning user dashboard)
- welcome.html (first visit)
- document_intake.html
- recognition.html
- briefcase.html
- timeline.html / timeline_auto_build.html
- calendar.html
- law_library.html
- eviction_answer.html
- counterclaim.html
- motions.html
- court_packet.html
- hearing_prep.html
- zoom_court.html
- letter_builder.html
- complaints.html
- contacts.html
- correspondence.html
- vault.html
- case.html

**CONSOLIDATE (Merge into core pages)**
- dashboard.html → home.html
- dashboard-v2.html → home.html
- my_tenancy.html → case.html
- documents.html → vault.html
- documents-v2.html → vault.html
- timeline-v2.html → timeline.html
- timeline-builder.html → timeline.html
- settings-v2.html → profile section

**DEPRECATE (Remove or archive)**
- index-simple.html
- evaluation_report.html
- mesh_network.html
- module-converter.html
- layout_builder.html
- style_editor.html
- page_editor.html

---

## Implementation Steps

### Phase 1: Navigation Fix (Immediate)
1. Update `shared-nav.js` with simplified 7-section structure
2. Add shared-nav to ALL active pages
3. Create `home.html` as returning user landing page

### Phase 2: Entry Flow
1. Update `welcome.html` for first-time users
2. Add session detection to route appropriately
3. Create progressive disclosure in intake

### Phase 3: Page Consolidation
1. Merge duplicate pages
2. Remove deprecated pages
3. Update all internal links

### Phase 4: Workflow Optimization
1. Add "Next Step" buttons on each page
2. Show progress indicator
3. Implement smart routing based on case status

---

## Quick Wins

1. **Add shared-nav to missing pages** - 1 line each
2. **Create home.html** - copy from dashboard, simplify
3. **Update welcome.html** - clear CTA flow
4. **Add progress bar** - show where user is in process

---

## Session/Routing Logic

```javascript
// On any page load:
function routeUser() {
    const hasSession = localStorage.getItem('semptify_user_id');
    const hasCase = localStorage.getItem('semptify_active_case');
    
    if (!hasSession) {
        // First visit → Welcome
        window.location.href = '/static/welcome.html';
    } else if (!hasCase) {
        // Has account, no case → Intake
        window.location.href = '/static/document_intake.html';
    } else {
        // Returning user → Home
        // (only redirect if on welcome page)
    }
}
```

---

## Success Metrics

- [ ] All pages have consistent navigation
- [ ] First-time user can start case in < 3 clicks
- [ ] Returning user sees case status immediately
- [ ] Clear "next step" from every page
- [ ] No dead-end pages
