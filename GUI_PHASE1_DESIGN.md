# GUI Phase 1 — Tenant Journal Restructuring Design Doc

> **Goal**: Restructure the tenant GUI around two pillars: RECORD and KNOW.
> A stressed tenant should be able to open Semptify and immediately see a timeline of everything that's happened, and a library of verified facts.

---

## 1. Product Direction (from project owner)

**PRIORITY #1**: User-friendly and simple. "Quick, Easy, and painless."

- Semptify is a DOCUMENT ORGANIZER for renters/tenants.
- Core function: Document everything between landlord and tenant throughout the tenancy.
- Keep good records of all interactions.
- The GUI must be simple enough for a stressed tenant to use immediately.

**PRIORITY #2**: Give the user "armour" to protect themselves.

- Information is straight-up FACTS. No opinions.
- The library/context engine surfaces verified facts only.

**TWO PILLARS**:

1. **RECORD** — Document capture, vault, timeline, journal. Big "Add Record" button everywhere.
2. **KNOW** — Library of verified facts, rights guides, context engine. Facts only, no opinions.

Everything else (advocate, manager, admin, legal) is secondary.
The tenant GUI = a timeline of everything that's happened + a library of facts.

---

## 2. Current State

### Pages (8 tenant-facing)
| Page | Purpose | Status |
| ------ | --------- | -------- |
| `tenant/index.html` | Dashboard with stat cards | Uses `main.css`, basic |
| `tenant/dashboard.html` | Hero + case summary + tools | Inline CSS, purple gradient |
| `tenant/journal.html` | Freeform journal entries | Inline CSS, blue theme |
| `tenant/documents.html` | Document vault grid | Inline CSS |
| `tenant/help.html` | Help/FAQ | Inline CSS |
| `tenant/law-library.html` | State laws lookup | Inline CSS |
| `tenant/tools/deadlines.html` | Deadline tracker | Inline CSS |
| `tenant/tools/letters.html` | Letter generators + signer | Inline CSS |

### Problems

- **8 pages, 8 different color schemes** — no visual consistency
- **No timeline view** — the #1 pillar (RECORD) has no dedicated page
- **Journal is freeform text only** — no structured event capture, no document linking
- **No "Add Record" button** — the core action has no prominent entry point
- **No Context Engine integration** — facts/stories not surfaced anywhere
- **Design system exists** (`ssot-design-system.css`, 1225 lines) but only 5 pages use it

### Assets Available

- `static/css/ssot-design-system.css` — full token system (colors, spacing, type, components)
- `static/components/feedback.js` — toast helper on 59 pages
- `static/components/loading-overlay.html` — spinner + button loading state
- `/api/page/{subject}` — Page Composer returns facts + stories + case data in one call
- `/api/context/subjects` — 13 subjects with labels
- `/api/context/facts` — verified facts with source URLs
- `/api/context/stories` — published tenant stories

---

## 3. Target Structure

### 3.1 Two-Pillar Navigation

```text
┌─────────────────────────────────────────────────┐
│  Semptify    [RECORD]  [KNOW]        [+ Add]  │
├─────────────────────────────────────────────────┤
│                                                 │
│  (pillar content — full width)                  │
│                                                 │
└─────────────────────────────────────────────────┘
```

- **RECORD tab** → Timeline view (default landing)
- **KNOW tab** → Library of verified facts
- **+ Add button** → Quick-capture modal (always visible, top right)

### 3.2 RECORD Pillar — Timeline First

The timeline is the home page. Everything the tenant has documented flows into one chronological stream.

**Layout**:

```text
┌─────────────────────────────────────────────────┐
│  Timeline                                       │
│  ┌───────────────────────────────────────────┐  │
│  │  Filter: [All] [Documents] [Events]      │  │
│  │          [Letters] [Deadlines]           │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌─── 2026-06-24 ───────────────────────────┐  │
│  │ 📄 lease.pdf uploaded          2:15 PM   │  │
│  │ 📝 Journal: "Landlord called about..."   │  │
│  │ ✉️ Repair letter generated     10:30 AM  │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌─── 2026-06-22 ───────────────────────────┐  │
│  │ 📸 inspection_photos.zip uploaded        │  │
│  │ ⚠️ Deadline: Rent due in 3 days          │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

**Data sources** (all existing):

- Timeline events: `GET /api/timeline` (existing)
- Documents: `GET /api/documents` (existing)
- Journal entries: `GET /api/journal` (existing)
- Deadlines: `GET /api/deadlines` (existing)
- Generated letters: `GET /api/letters` (existing)

**New work**: One aggregator endpoint `GET /api/tenant/feed` that merges all of the above into a single chronological stream, OR frontend merges client-side. Backend aggregator is cleaner.

### 3.3 KNOW Pillar — Library of Facts

**Layout**:

```text
┌─────────────────────────────────────────────────┐
│  Library                                        │
│  ┌───────────────────────────────────────────┐  │
│  │  What do you need help with?              │  │
│  │  [Eviction] [Repair] [Deposit] [Rent]    │  │
│  │  [Lease] [Safety] [Habitability] ...     │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌─── Eviction Defense ─────────────────────┐  │
│  │  VERIFIED FACTS                           │  │
│  │  • Minn. Stat. § 504B — source: MN Revisor│  │
│  │  • Court record: Smith v. Jones — source  │  │
│  │                                           │  │
│  │  TENANT STORIES                           │  │
│  │  📖 "I avoided court by documenting..."   │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

**Data source**: `GET /api/page/{subject}` — Page Composer already returns facts + stories in one call.

**13 subjects** (from Context Engine taxonomy):
eviction, repair, rent, lease, deposit, discrimination, safety, habitability, retaliation, small_claims, court_prep, evidence, timeline

### 3.4 Add Record Modal — Always Available

```text
┌─────────────────────────────────┐
│  + Add Record              [×]  │
│                                 │
│  What happened?                 │
│  ┌─────────────────────────┐    │
│  │  Journal entry          │    │
│  │  Upload document        │    │
│  │  Generate letter        │    │
│  │  Add deadline           │    │
│  │  Log interaction        │    │
│  └─────────────────────────┘    │
│                                 │
│  Quick journal:                 │
│  ┌─────────────────────────┐    │
│  │  Type here...           │    │
│  │                         │    │
│  └─────────────────────────┘    │
│  [Save to timeline]             │
└─────────────────────────────────┘
```

This is the big "Add Record" button from the product direction. It's a modal that opens from the top-right `+ Add` button on every page.

---

## 4. Page Consolidation

### Current 8 pages → New 4 pages

| Current | New | Action |
|---------|-----|--------|
| `tenant/index.html` | **Remove** — replaced by timeline | Redirect to `/tenant/timeline.html` |
| `tenant/dashboard.html` | **Remove** — stats fold into timeline header | Redirect to `/tenant/timeline.html` |
| `tenant/journal.html` | **Merge into timeline** — journal entries are timeline events | Journal entry = timeline event with type 'journal' |
| `tenant/documents.html` | **Keep** — document vault grid | Add "Add Record" button, link from timeline |
| `tenant/help.html` | **Keep** — help/FAQ | Restyle with design system |
| `tenant/law-library.html` | **Replace with KNOW pillar** — `/tenant/library.html` | Uses Page Composer |
| `tenant/tools/deadlines.html` | **Keep** — deadline tracker | Add "Add Record" button |
| `tenant/tools/letters.html` | **Keep** — letter generators | Add "Add Record" button |

### New pages to build

| Page | Purpose |
| ------ | --------- |
| `tenant/timeline.html` | **RECORD pillar** — merged chronological feed (new home page) |
| `tenant/library.html` | **KNOW pillar** — subject grid + facts + stories via Page Composer |
| `tenant/add-record.html` | **Add Record modal** — quick capture (could be a modal component instead of a page) |

---

## 5. Design System Adoption

All new pages use `ssot-design-system.css` via:

```html
<link rel="stylesheet" href="/static/css/ssot-design-system.css">
```

No inline `<style>` blocks. No per-page color variables. The design system has:

- Color tokens (`--color-primary`, `--color-success`, etc.)
- Spacing scale (`--space-1` through `--space-16`)
- Typography scale (`--text-xs` through `--text-4xl`)
- Component classes (`.card`, `.btn`, `.btn--primary`, `.input`, etc.)
- Layout utilities (`.container`, `.grid`, `.flex`)

### Theme

Use the existing `royal` theme (purple) as default — it's already on `tenant/index.html` via `data-theme="royal"`. The design system supports themes via `data-theme` attribute.

---

## 6. Implementation Plan

### Step 1: Build the aggregator endpoint

- `GET /api/tenant/feed` — merges timeline events, documents, journal entries, deadlines, letters into one chronological stream
- Returns: `[{type, title, timestamp, metadata, link}]`
- This is the backend for the RECORD pillar

### Step 2: Build `tenant/timeline.html`

- Uses `ssot-design-system.css`
- Fetches `/api/tenant/feed`
- Filter chips: All / Documents / Events / Journal / Letters / Deadlines
- Grouped by day with date headers
- Each item links to its source (document, journal entry, etc.)
- "Add Record" button in header

### Step 3: Build `tenant/library.html`

- Uses `ssot-design-system.css`
- Subject grid (13 subjects from `/api/context/subjects`)
- Click a subject → fetch `/api/page/{subject}` → show facts + stories
- Facts section: verified facts with source URLs (no hallucination)
- Stories section: published tenant stories (avoided_court hero frame)

### Step 4: Build the Add Record modal

- Component included on every tenant page
- Quick journal entry (text + save to timeline)
- Links to: upload document, generate letter, add deadline
- Uses `SemptifyFeedback` for success/error

### Step 5: Redirect old pages

- `/tenant/` → `/tenant/timeline.html`
- `/tenant/dashboard.html` → `/tenant/timeline.html`
- `/tenant/journal.html` → `/tenant/timeline.html` (journal entries are in the feed)
- `/tenant/law-library.html` → `/tenant/library.html`

### Step 6: Restyle remaining pages

- `tenant/documents.html` — adopt design system
- `tenant/help.html` — adopt design system
- `tenant/tools/deadlines.html` — adopt design system
- `tenant/tools/letters.html` — adopt design system

---

## 7. Backend Endpoints Needed

| Endpoint | Status | Notes |
| ---------- | -------- | ------- |
| `GET /api/tenant/feed` | **NEW** | Aggregator: timeline + documents + journal + deadlines + letters |
| `GET /api/page/{subject}` | ✅ Exists | Page Composer — facts + stories + case data |
| `GET /api/context/subjects` | ✅ Exists | 13 subjects with labels |
| `GET /api/timeline` | ✅ Exists | Timeline events |
| `GET /api/documents` | ✅ Exists | Document vault |
| `GET /api/journal` | ✅ Exists | Journal entries |
| `GET /api/deadlines` | ✅ Exists | Deadline tracker |
| `GET /api/letters` | ✅ Exists | Generated letters |

Only one new endpoint needed: `/api/tenant/feed`.

---

## 8. What This Unblocks

Once this design doc is approved:

1. **Build `/api/tenant/feed`** — one new backend endpoint
2. **Build 3 new pages** — timeline, library, add-record modal
3. **Redirect 4 old pages** — simple route changes
4. **Restyle 4 remaining pages** — adopt design system
5. **Then: full GUI design can be planned** for advocate, manager, legal, admin roles

---

## 9. Open Questions

1. **Should the timeline support manual event creation?** (e.g., "Called landlord about broken heater") — Yes, via the Add Record modal's quick journal.
2. **Should the library show stories by default or only after clicking a subject?** — Default to subject grid, stories appear after selecting a subject.
3. **Should the Add Record modal be a page or a true modal?** — Modal component, included on every tenant page. Falls back to a page on mobile if needed.
4. **What happens to the existing `tenant/index.html` dashboard stats?** — Fold the most useful ones (document count, upcoming deadlines) into the timeline header as small badges.

---

*Created 2026-06-25. This is the design doc for GUI Phase 1 — Tenant Journal Restructuring.*
