# Document Center (DC) — Design & Build Plan

> Produced: 2026-06-27 | Based on: DOCUMENT_CENTER_PLAN.md + DC_HANDOFF_SONNET.md
> Status: Design + planning complete. Implementation lives in `app/modules/document_center/`; tests pass and page is live.

---

## 1. Executive Summary

The Document Center (DC) is Semptify's flagship product surface — a single 3-pane desktop page where a tenant works with their documents alongside Semptify. The left pane lists vault documents; the center pane renders the selected document in the Semptify Viewer; the right pane shows document-process overlays with per-overlay completion %. As the tenant and Semptify walk through a document together — confirming OCR-extracted dates, parties, addresses, and amounts — overlays fill up. When enough verified metadata accumulates, new Semptify features unlock progressively (Timeline → Journal → Contact Manager → Case Builder). The tenant always sees what Semptify sees. Nothing is hidden. Nothing auto-files. The DC replaces every fragmented document UI that exists today with one unified workspace.

---

## 1b. Document Processing Pipeline (Audit Findings — 2026-06-27)

### What Already Exists (do NOT rebuild)

| Component | File | What It Does |
|-----------|------|-------------|
| Intake router | `app/modules/intake/router.py` | `POST /api/intake/upload/auto` — THE one upload entry point |
| Intake engine | `app/services/document_intake.py` | `DocumentClassifier` + `DataExtractor` |
| Overlay types | `app/core/overlay_types.py` | `DOCUMENT_EXTRACTION`, `DOCUMENT_CLASSIFICATION`, `PARTY_EXTRACTION`, `TIMELINE_EXTRACTION`, `HIGHLIGHT`, `NOTE`, `FOOTNOTE` — all exist |
| Overlay manager | `app/services/unified_overlay_manager.py` | `create_overlay()`, `get_overlays()`, `compose_document_view()` |
| Flow orchestrator | `app/modules/intake/service.py` | `DocumentFlowOrchestrator.process_document_complete()` |

### The Full Pipeline (what happens on every upload)

```
TENANT UPLOADS FILE
        │
        ▼
[POST /api/intake/upload/auto]
        │
        ├─► NOTARIZE ─────────────────────────── SHA-256 receipt → notarization_id
        │                                        Tamper-proof before anything else
        │
        ├─► VAULT STORE ─────────────────────── File → user cloud (Google/Dropbox)
        │                                        → vault_id + storage_path
        │
        ├─► INTAKE REGISTER ─────────────────── doc_id created, status = RECEIVED
        │
        ├─► EXTRACT (background) ────────────── DocumentClassifier → doc_type + confidence
        │      │                                DataExtractor → dates, parties, amounts,
        │      │                                                 addresses, clauses
        │      │                                status: EXTRACTING → ANALYZING → COMPLETE
        │      │
        │      └─► FLOW ORCHESTRATION ─────── DocumentFlowOrchestrator:
        │                                      - Timeline events created
        │                                      - FormData hub updated
        │                                      - Issues detected + laws matched
        │                                      - Chain of custody tracking
        │
        └─► EVENT: DOCUMENT_PROCESSED ───────── Downstream systems react
                                                (timeline, briefcase, deadlines)

⚠️ THE GAP: Extraction results stored in intake engine's internal storage.
            NOT yet written to UnifiedOverlayManager (user's cloud vault overlays).
            This is the BRIDGE the DC service.py must build.
```

### The Bridge (what DC service.py must add)

After `DOCUMENT_PROCESSED` event fires, DC service converts intake results into overlays:

```python
# DC service.py — bridge_intake_to_overlays(doc_id, vault_id, vault_path, user_id)

# 1. Classification → DOCUMENT_CLASSIFICATION overlay
await manager.create_overlay(
    CreateOverlayRequest(
        overlay_type=OverlayType.DOCUMENT_CLASSIFICATION,
        document_id=vault_id,
        vault_path=vault_path,
        payload={"doc_type": doc_type, "confidence": confidence},
        metadata={"source": "intake_auto"},
        ephemeral=False,
    )
)

# 2. Parties → PARTY_EXTRACTION overlay
# 3. Dates + Amounts → DOCUMENT_EXTRACTION overlay
# 4. Timeline events → TIMELINE_EXTRACTION overlay
```

Once overlays exist in the user's vault, the DC viewer can read them and show completion %.

### User Metadata Cross-Reference (the fact-check layer)

When extraction runs, the DC service should cross-reference extracted data against the user's known metadata:
- **Address match**: extracted property address vs. address on user profile → pre-suggest as confirmed
- **Contact match**: extracted party name vs. existing contacts → suggest "Is this [known contact]?"
- **Mismatch flag**: extracted data contradicts known metadata → flag for user review with "Semptify noticed a difference"

This is NOT a blocking step. It's a suggestion layer. User is always the final authority.

### Processing Status (what tenant sees while pipeline runs)

| Stage | Status Label in DC | What Shows in Right Pane |
|-------|--------------------|--------------------------|
| Uploaded, not yet processed | "Waiting" | Right pane: "Processing will begin shortly..." |
| `EXTRACTING` | "Reading" | Spinner on OCR overlay row |
| `ANALYZING` | "Analyzing" | Spinners on Parties, Dates, Amounts rows |
| `COMPLETE` (extraction done, no overlays yet) | "Processing" | DC bridge running |
| Overlays written | "Ready to Review" | All overlay rows populate with initial % |
| User confirms fields | "In Review" | % bars fill as user confirms |
| All required fields confirmed | "Verified ✅" | Overall badge turns green, unlocks fire |

### Q2 Answered: When Does Processing Run?

**Auto, immediately on upload, in the background.** This is already how `upload/auto` works. The DC inherits this — when tenant opens a document in the viewer, processing is already done or in progress. They never need to click "Process." They just open and confirm.

---

## 2. Information Architecture

### 2a. 3-Pane Layout

```
+====================+==========================================+======================+
|  LEFT PANE         |  CENTER PANE                             |  RIGHT PANE          |
|  Vault List        |  Semptify Viewer                         |  Overlays Panel      |
|  (280px fixed)     |  (flex fill)                             |  (320px fixed)       |
+====================+==========================================+======================+
|                    |  [VIEWER TOP BAR]                        |                      |
|  [+ Upload]        |  ← Back | doc-name.pdf | 🏷 Type ▾ |    |  📄 lease.pdf        |
|  ──────────        |  🖊 Highlight | 📝 Note | 🔗 Reference  |  ── Overlays ───────  |
|                    |  | Download | Share | Delete            |                      |
|  🔍 Search docs    |  ─────────────────────────────────────── |  ⬜ OCR Extraction   |
|                    |                                          |  ████████░░  82%     |
|  All (12)          |                                          |  Goal: Extract text  |
|  Unverified (4)    |  +----- VIEWER FRAME ------------------+ |  [Open ▾]            |
|  In Review (3)     |  |                                     | |                      |
|  Verified (5)      |  |  [PDF.js / image / fallback]        | |  ✅ Parties          |
|                    |  |                                     | |  ██████████  100%    |
|  ── Documents ───  |  |  Semptify highlights (yellow)       | |  Goal: All parties   |
|  📄 lease.pdf      |  |  User highlights (blue)             | |  [Open ▾]            |
|    ✅ Verified     |  |  Notes (📝 pins)                    | |                      |
|  📄 notice.pdf     |  |  References (🔗 pins)               | |  ⬜ Dates            |
|    🔄 In Review    |  |                                     | |  ██████░░░░  58%     |
|  📄 receipt.pdf    |  |  [Confirm? field popover]           | |  Goal: All dates     |
|    ⬜ Unverified   |  |                                     | |  [Open ▾]            |
|  ...               |  +-------------------------------------+ |                      |
|                    |                                          |  ⬜ Amounts           |
|                    |  [Page 1 of 4] [◀ ▶] [Zoom -/+]        |  ███░░░░░░░  30%     |
|                    |                                          |  Goal: Rent + deposit|
|                    |                                          |  [Open ▾]            |
|                    |                                          |                      |
|                    |                                          |  ── Overall ─────────|
|                    |                                          |  Verified: 68%       |
|                    |                                          |  ████████░░          |
|                    |                                          |                      |
|                    |                                          |  🔓 Timeline (unlocked)|
|                    |                                          |  🔒 Journal (needs 80%)|
+--------------------+------------------------------------------+----------------------+
```

### 2b. Viewer Top Bar — Selected Item Options

| Control | Action |
|---------|--------|
| `← Back` | Deselect document, return to list-only state |
| `doc-name.pdf` | (read-only label) |
| `🏷 Type ▾` | Declare/change document type (Lease, Notice, Receipt, ...) |
| `🖊 Highlight` | Enter highlight mode (draws yellow region on click-drag) |
| `📝 Note` | Enter note mode (places note pin on click) |
| `🔗 Reference` | Enter reference mode (links selected region to another doc or contact) |
| `Download` | Download original from vault |
| `Share` | Open share dialog (tenant-controlled) |
| `Delete` | Soft-delete with confirmation |

### 2c. Left Pane — Document List Row

```
📄  lease.pdf                    ✅ Verified
    Lease Agreement  |  Jun 3, 2026  |  4 overlays
```

Fields: icon, filename, verification badge, document type label, upload date, overlay count.
Click anywhere on row → opens in viewer.

### 2d. Right Pane — Overlay Row Template

```
[status-icon]  [Overlay Name]
[progress-bar████████░░]  [nn%]
Goal: [one-line description of what 100% means]
[Open ▾]  (expands inline detail or opens side-drawer)
```

Status icons: `⬜` = not started, `🔄` = in progress, `✅` = complete, `⚠️` = needs attention.

### 2e. Unlock Indicator (bottom of right pane)

Shows currently unlocked features + next threshold:
```
🔓 Timeline — unlocked
🔒 Journal — needs 80% overall verified (currently 68%)
🔒 Contact Manager — needs Parties overlay 100%
```

No toast spam. One quiet indicator that updates as progress fills.

---

## 3. Viewer Design

### 3a. Document Rendering Strategy

| File Type | Renderer | Fallback |
|-----------|----------|----------|
| `.pdf` | PDF.js (embedded, `pdfjs-dist` 3.x, Python 3.11.9 compatible CDN) | Server-side convert to images |
| `.jpg`, `.png`, `.webp` | `<img>` tag in scrollable frame | — |
| `.docx` | Server converts to PDF on first open (python-docx → reportlab) | Download prompt |
| `.html` | Sandboxed `<iframe sandbox="allow-same-origin">` | Download prompt |
| `.txt` | `<pre>` in styled frame | — |

Conversion happens once, result cached in vault. No re-conversion on every open.

### 3b. Two Annotation Layers

The viewer frame has two stacked layers:

1. **Document layer** — the rendered PDF.js canvas or `<img>`
2. **Annotation layer** — absolute-positioned SVG/div overlay on top

**Semptify extraction highlights** (auto, from OCR/overlays):
- Color: amber/yellow `rgba(255, 200, 0, 0.35)`
- Border: `2px solid #f59e0b`
- Tooltip on hover: shows extracted field name + extracted value + "Confirm?" button

**User highlights** (manual, from Highlight tool):
- Color: blue `rgba(59, 130, 246, 0.25)`
- Border: `2px dashed #3b82f6`
- Tooltip: shows user's note text (if any)

**Note pins** `📝`:
- Small icon pinned to document region
- Click to expand note text

**Reference pins** `🔗`:
- Small icon pinned to region
- Click to see what it links to (doc or contact)

### 3c. Inline Confirm/Correct Popover

When Semptify highlights a field, clicking it opens a small popover:

```
┌─────────────────────────────────┐
│ 🟡 Semptify read this as:       │
│   "Landlord: J. Smith"          │
│                                 │
│ [✓ Confirm]  [✎ Correct]        │
└─────────────────────────────────┘
```

"Correct" opens a small text input pre-filled with the extracted value. User edits and saves. The overlay updates immediately; completion % recalculates.

### 3d. Walk-Through Modes

Two modes, user picks via a toggle in the top bar:

| Mode | Behavior |
|------|----------|
| **Step Mode** | Semptify steps through extracted fields one at a time. "Next field →" button. Good for first review. |
| **Live Mode** | All Semptify highlights visible at once. User clicks any field to confirm/correct. Good for returning. |

Default: **Live Mode** (less hand-holding for the stressed tenant who just wants to confirm quickly).

---

## 4. Overlay Panel Design

### 4a. Overlay Types Per Document Category

These map to `OverlayType` values from `app/core/overlay_types.py`. New DC-specific types will be added to that enum.

| Overlay Name | Internal Type Suggestion | Goal (100% definition) |
|---|---|---|
| OCR Extraction | `ocr_extraction` | All readable text extracted, no unreadable regions flagged |
| Parties | `parties_extraction` | Landlord + tenant names confirmed by user |
| Dates | `dates_extraction` | All date fields confirmed (start, end, notice dates, etc.) |
| Addresses | `addresses_extraction` | Property address confirmed, mailing address if different |
| Amounts | `amounts_extraction` | Rent, deposit, fees all confirmed |
| Signatures | `signatures_detection` | Presence/absence of signatures confirmed |
| Document Type | `type_verification` | User confirmed document type matches content |
| User Annotations | `user_annotations` | At least 1 user note or highlight added (optional, never blocks unlock) |

### 4b. Completion % Calculation (per overlay)

```
completion = confirmed_fields / required_fields_for_type * 100
```

Example for Parties overlay on a Lease:
- Required fields: landlord_name, tenant_name (= 2)
- Confirmed: landlord_name only (= 1)
- Completion: 50%

Each overlay has a `required_fields` list defined in `app/core/document_types.py`.
An overlay reaches 100% when all required fields for the stated document type are confirmed.

### 4c. Overall Verified Score

```
overall_score = (sum of all overlay completions) / (number of overlays)
```

This is the number that drives the unlock pattern.

### 4d. Expanded Overlay Detail View

When user clicks "Open ▾" on an overlay row, it expands inline:

```
✅ Parties  100%
Goal: All parties identified and confirmed.
──────────────────────────────────────
  ✅  Landlord name:    "James Smith"        [Edit]
  ✅  Tenant name:      "Maria Gonzalez"     [Edit]
  ✅  Witnesses:        "None listed"        [Edit]
──────────────────────────────────────
[Jump to page 1 where landlord appears]
```

"Jump to page X" scrolls the viewer to the relevant page and flashes the relevant highlight.

---

## 5. Unlock Rules

| Unlock | Feature | Threshold | What Triggers It |
|--------|---------|-----------|-----------------|
| 1st | **Timeline View** | 1 document with Dates overlay ≥ 80% AND Parties overlay ≥ 80% | At least one doc where we know who + when |
| 2nd | **Tenant Journal** | Overall verified score ≥ 60% across any 2 documents | Meaningful doc collection beginning |
| 3rd | **Contact Manager** | Parties overlay = 100% on any 1 document | We know at least one real contact |
| 4th | **Case Builder** | 3+ documents verified (overall ≥ 80% each) | Enough evidence to start a case |
| Future | Legal Prep, Advocates | TBD | Future planning |

**How unlocks surface:**
- Right pane unlock indicator updates silently (no toast spam)
- First time a feature unlocks: one calm inline banner: "📅 Timeline is now available." with a link
- The banner appears once, then collapses to the lock indicator permanently showing 🔓
- No confetti. No celebration modal. Tenant is stressed — keep it calm.

---

## 6. Per-Document-Type Checklists (First 5)

SSOT lives in: `app/core/document_types.py` (new file, see Section 7).

### Lease Agreement (`lease`)
| Field | Type | Required | OCR Target |
|-------|------|----------|-----------|
| landlord_name | text | ✅ | "Landlord:", "Owner:", signature block |
| tenant_name | text | ✅ | "Tenant:", "Lessee:", signature block |
| property_address | text | ✅ | "Premises:", "Property Address:" |
| lease_start_date | date | ✅ | "commencing", "beginning", "start date" |
| lease_end_date | date | ✅ | "ending", "terminating", "expiration" |
| monthly_rent | currency | ✅ | "$", "monthly rent", "rent amount" |
| security_deposit | currency | ✅ | "deposit", "security deposit" |
| signatures_present | boolean | ✅ | signature lines detected |
| late_fee | currency | ⬜ optional | "late fee", "late charge" |
| pet_policy | text | ⬜ optional | "pets", "animals" |

**Verified when:** all 8 required fields confirmed.

### Notice to Vacate (`notice_to_vacate`)
| Field | Type | Required | OCR Target |
|-------|------|----------|-----------|
| sender_name | text | ✅ | header, "From:", signature |
| recipient_name | text | ✅ | "To:", "Dear" |
| notice_date | date | ✅ | document date, letterhead |
| vacate_by_date | date | ✅ | "vacate by", "on or before", "must leave" |
| property_address | text | ✅ | "located at", "premises at" |
| reason_stated | text | ✅ | "reason for notice", body paragraph |
| delivery_method | text | ⬜ optional | "hand-delivered", "certified mail" |

**Verified when:** all 6 required fields confirmed.

### Repair Request (`repair_request`)
| Field | Type | Required | OCR Target |
|-------|------|----------|-----------|
| date_submitted | date | ✅ | document date |
| tenant_name | text | ✅ | "From:", "submitted by" |
| property_address | text | ✅ | address block |
| issue_description | text | ✅ | body / issue description |
| landlord_notified | text | ✅ | "sent to", "submitted to", "attention" |
| response_deadline | date | ⬜ optional | "please respond by" |

**Verified when:** all 5 required fields confirmed.

### Rent Receipt (`rent_receipt`)
| Field | Type | Required | OCR Target |
|-------|------|----------|-----------|
| payment_date | date | ✅ | "received", "date" |
| amount_paid | currency | ✅ | "$", "amount" |
| payer_name | text | ✅ | "received from", "paid by" |
| receiver_name | text | ✅ | "received by", signature |
| period_covered | text | ✅ | "for rent", "for the month of" |
| receipt_number | text | ⬜ optional | "receipt #", "invoice #" |

**Verified when:** all 5 required fields confirmed.

### Move-in Inspection (`move_in_inspection`)
| Field | Type | Required | OCR Target |
|-------|------|----------|-----------|
| inspection_date | date | ✅ | document date |
| property_address | text | ✅ | address block |
| tenant_name | text | ✅ | "Tenant:" |
| landlord_or_agent | text | ✅ | "Landlord:", "Agent:" |
| condition_notes | text | ✅ | room-by-room entries, checkboxes |
| both_signed | boolean | ✅ | signature lines |

**Verified when:** all 6 required fields confirmed.

---

## 7. Code Structure

### New Files (all additive — do not touch existing modules)

```
app/
├── core/
│   └── document_types.py          [NEW] SSOT for doc type defs + required field checklists
│
├── modules/
│   └── document_center/           [NEW MODULE]
│       ├── __init__.py
│       ├── router.py              REST endpoints (list docs, get doc, overlays for doc, unlock status)
│       ├── service.py             DC business logic (orchestrates vault SDK + overlay manager)
│       ├── viewer.py              Document rendering helpers (PDF conversion, MIME detection)
│       └── register.py            FunctionGroupContract registrations
│
app/templates/
├── pages/
│   └── document_center.html       [NEW] 3-pane page template (extends base.html)
│
├── partials/dc/                   [NEW] Jinja partials for each pane
│   ├── vault_list.html            Left pane: document list rows
│   ├── viewer_frame.html          Center pane: viewer + top bar
│   ├── overlay_panel.html         Right pane: overlay rows + unlock indicator
│   └── overlay_detail.html        Expanded overlay detail (loaded via HTMX swap)
│
static/
├── js/dc/                         [NEW]
│   ├── viewer.js                  PDF.js wrapper + annotation layer management
│   ├── panel.js                   Right pane overlay rows + expand/collapse
│   └── unlock.js                  Unlock threshold checking + banner display
│
└── css/components/
    └── dc.css                     [NEW] All DC-specific styles (3-pane layout, annotation colors)
```

### Existing Files to REUSE (do not modify)

| File | Used For |
|------|----------|
| `app/sdk/vault/client.py` | `VaultClient` — list vault files, get file URL |
| `app/services/unified_overlay_manager.py` | `UnifiedOverlayManager` — create, get, update overlays |
| `app/core/overlay_types.py` | `OverlayType` enum — real overlay type values |
| `app/core/navigation.py` | `navigation.get_stage()` — SSOT URL paths (no hardcoding) |
| `app/core/utc.py` | `utc_now()` — all timestamps |
| `app/core/module_contracts.py` | `register_function_group()` — DC API contracts |
| `app/templates/base.html` | Base template (DC page extends this) |
| `static/components/feedback.html` | `SemptifyFeedback` — all user-facing messages |

### Key API Contracts to Register (in `register.py`)

```
dc::document_list       — list vault docs with overlay status
dc::document_select     — get single doc + all overlays + viewer URL
dc::overlay_confirm     — confirm or correct a field in an overlay
dc::unlock_status       — get current unlock state for user
```

### Overlay API Usage (real signatures — do not invent)

```python
# Create overlay (e.g. OCR extraction result)
await manager.create_overlay(
    CreateOverlayRequest(
        overlay_type=OverlayType.OCR_EXTRACTION,  # real enum value
        document_id=doc_id,
        vault_path=vault_path,
        payload={"extracted_fields": {...}},
        metadata={"confidence": 0.92},
        ephemeral=False,
    )
)

# Query overlays for a document
response = await manager.get_overlays(document_id=doc_id)

# Compose view (for viewer rendering with overlays applied)
view = await manager.compose_document_view(
    document_id=doc_id,
    overlay_ids=[o.overlay_id for o in response.overlays],
    apply_redactions=True,
)
```

---

## 8. Build Slices

### Slice 1 — 3-Pane Shell (no real data)

**What's in it:**
- `document_center.html` template with CSS 3-pane layout
- `dc.css` with fixed left/right pane widths, flex center
- `vault_list.html` partial rendering a hardcoded list of 3 fake documents
- `viewer_frame.html` partial rendering a hardcoded PDF.js skeleton (no real doc)
- `overlay_panel.html` partial with 3 hardcoded overlay rows at fake %s
- Route `/dc` registered in `app/core/product_manifest.py` → `app/modules/document_center/router.py`

**Testable:** Navigate to `/dc`, see 3-pane layout. Click a fake doc row, viewer frame header changes. Overlay rows show progress bars. No data calls, nothing breaks.

**Dependencies:** None beyond base.html, dc.css, PDF.js CDN.

---

### Slice 2 — Live Vault List

**What's in it:**
- `app/modules/document_center/service.py` → `list_documents(user_id)` calls `VaultClient.list_files()`
- Left pane populated from real vault API
- Each row shows: filename, upload date, document type badge (if declared), verification state badge
- HTMX: selecting a row loads `viewer_frame.html` partial for that doc into center pane
- Endpoint: `GET /api/dc/documents` → returns list of vault docs with overlay summary per doc

**Testable:** Real vault docs appear in left pane. Clicking one updates the viewer top bar with the real filename. Overlay panel shows "No overlays yet" if none exist.

**Dependencies:** `app/sdk/vault/client.py`, `app/services/unified_overlay_manager.py` (for overlay count per doc).

---

### Slice 3 — Viewer Renders Real PDF

**What's in it:**
- `app/modules/document_center/viewer.py` → `get_viewer_url(vault_path, access_token)` returns a short-lived signed URL
- `viewer.js` → PDF.js loads the URL, renders the PDF in the center pane
- Page navigation (◀ ▶) and zoom (+/-) wired
- MIME detection: if not PDF, render `<img>` or show "Unsupported — Download" button
- Endpoint: `GET /api/dc/documents/{doc_id}/view-url` → returns `{url, mime_type, pages}`

**Testable:** Select a real PDF from vault, it renders in the viewer. Navigate pages. Select an image file, it renders as `<img>`.

**Dependencies:** VaultClient, signed URL from storage provider (Google Drive / Dropbox file download URL).

---

### Slice 4 — OCR Overlay + Semptify Highlights

**What's in it:**
- `app/modules/document_center/service.py` → `run_ocr_overlay(doc_id, vault_path, user_id)` calls OCR, stores result via `UnifiedOverlayManager.create_overlay()`
- Annotation layer in `viewer.js` reads the overlay payload and draws Semptify highlights (amber) at the extracted text regions
- Right panel OCR row shows real completion %
- Click a Semptify highlight → confirm/correct popover appears
- Confirming a field calls `PATCH /api/dc/overlays/{overlay_id}/confirm` → updates payload, recalculates %

**Testable:** Open a doc, OCR runs (or is already cached), amber highlights appear on the document, right pane OCR row shows a real %. Confirming a field updates the % live.

**Dependencies:** OCR service (existing or `pytesseract` / external API), `UnifiedOverlayManager`.

---

### Slice 5 — Document Type Declaration + First Checklist (Lease)

**What's in it:**
- `app/core/document_types.py` → `DOCUMENT_TYPES` dict with Lease definition + required fields
- Top bar "🏷 Type ▾" dropdown lets user declare the document type
- Once type is declared: right pane shows ALL relevant overlays for that type (Parties, Dates, Amounts, Signatures)
- Each overlay row shows the correct required fields when expanded
- Overlay completions now calculated against the type-specific required field list
- Endpoint: `POST /api/dc/documents/{doc_id}/type` → sets document type, triggers re-extraction for known fields

**Testable:** Open a lease PDF, declare type "Lease Agreement", right pane updates to show Parties/Dates/Amounts/Signatures overlays, each at 0%. Confirm one field, % increments correctly.

**Dependencies:** `document_types.py` (new), all overlays from Slice 4.

---

### Slice 6 — User Annotations (Highlights, Notes, References)

**What's in it:**
- `viewer.js` → Highlight mode: click-drag draws user highlight (blue), stores region coords
- Note mode: click places a pin, opens a text input, saves note text
- Reference mode: click selects region, then user picks another doc or contact to link
- All annotations stored as overlays via `UnifiedOverlayManager.create_overlay()` with `overlay_type=USER_ANNOTATION` (or equivalent real enum)
- User key: all annotations carry `created_by=user_id` (the user's key is their `user_id` from the session)
- Annotations survive page reload (loaded from overlay storage on document open)
- Endpoint: `POST /api/dc/documents/{doc_id}/annotate` → wraps create_overlay for annotation types

**Testable:** Highlight a region in blue, refresh the page, highlight persists. Add a note pin, text saves. All annotation overlays appear in right panel under "User Annotations" row.

**Dependencies:** `UnifiedOverlayManager`, user session `user_id`.

---

### Slice 7 — Progressive Unlocks (Timeline first)

**What's in it:**
- `app/modules/document_center/service.py` → `get_unlock_status(user_id)` computes unlock thresholds across all user's documents
- `unlock.js` polls `/api/dc/unlock-status` after every field confirmation, updates right pane indicator
- Timeline unlock fires when: any 1 doc has Dates overlay ≥ 80% AND Parties overlay ≥ 80%
- Unlock banner appears once in right pane: "📅 Timeline is now available." with link
- Banner dismisses after user clicks through; indicator permanently shows 🔓
- Journal and Contact Manager unlocks implemented the same way (see Section 5 thresholds)
- Endpoint: `GET /api/dc/unlock-status` → returns `{timeline: bool, journal: bool, contacts: bool, scores: {...}}`

**Testable:** Confirm enough fields on a lease to hit Timeline threshold, right pane updates to show 🔓 Timeline with link. Navigating to /tenant/timeline works (already exists).

**Dependencies:** All previous slices, `app/modules/timeline/router.py` (existing), `navigation.get_stage('timeline')` for SSOT link.

---

## 9. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Large PDF freezes browser (> 50 pages) | High | PDF.js lazy loads pages; only render visible page + 1 page buffer. Show page count warning for > 100 pages. |
| OCR accuracy on photos/scans | Medium | Always show confidence score alongside extraction. Never mark confirmed without user action. User is the final authority. |
| Storage for annotation overlays | Medium | Annotations are overlays stored in user's own cloud vault (Google Drive / Dropbox). Not on Semptify servers. Aligns with privacy mandate. |
| .docx conversion introduces formatting errors | Medium | Show "converted from .docx — some formatting may differ" banner. Keep original in vault; render the conversion only. |
| DC becomes a giant IDE (scope creep) | High | 5 verbs only: Upload, Store, Process, Review, Share. Any new verb requires explicit approval. Slices 1-7 above are the full scope for v1. |
| Tenant overwhelmed by too many overlay rows | Medium | Collapse all overlays by default. Show only the 2-3 most incomplete. "Show all" expands the rest. |
| Render 30s Cloudflare timeout on OCR | Medium | OCR runs as a background task (FastAPI `BackgroundTasks`). Returns `{status: "processing"}` immediately. Client polls `/api/dc/documents/{id}/status` until done. |
| Mobile breakpoints | Low | Deferred. CSS uses `@media` queries but only desktop is designed in v1. Left + right panes collapse to tabs on small screens automatically (future). |

---

## 10. Open Questions for the User

| # | Question | Options | Impact |
|---|----------|---------|--------|
| 1 | **Which document types ship in Slice 5?** | Suggest the 5 listed above | Determines `document_types.py` initial content |
| 2 | **Does OCR run automatically on upload, or only when user opens the document?** | Auto (background task on upload) vs. On-demand (when user clicks Review) | Affects UX — auto is seamless, on-demand is more visible/trustworthy |
| 3 | **Should Semptify suggest the document type, or does the tenant declare it?** | AI suggests (tenant confirms) vs. Tenant declares from dropdown | AI suggest is friendlier but adds complexity; declare is simpler and honest |
| 4 | **Where does the annotation overlay storage live when the user hasn't connected cloud storage?** | Block annotations until storage connected (gate) vs. Store in Semptify R2 temporarily with a "save to your vault" prompt | Affects onboarding dependency |
| 5 | **What OverlayType enum values already exist in `app/core/overlay_types.py`?** | Read the file before Slice 4 | Determines which new OverlayType values need to be added |
| 6 | **Should the DC replace the existing `/documents` page, or run alongside it?** | Replace (one unified page) vs. Alongside (DC is a "power mode") | Replacing is cleaner; alongside avoids breaking existing references |
| 7 | **What is the URL for the DC?** | `/dc`, `/documents`, `/tenant/documents`, `/tenant/center` | SSOT navigation registration |

---

## 11. Broader Context — Semptify's Mission

The DC is the mechanical core of a larger mission:

**semptify.org** (the public umbrella) exists to connect tenants facing housing problems with:
- Tools to organize evidence, meet deadlines, document conditions
- Advocates, housing counselors, tenant unions
- Legal aid organizations, free rights information
- Each other (community, not commerce)

**The tenant app** (what logged-in users see) = the DC + features that unlock from it.
The semptify.org public site and the tenant app are separate builds. The DC is the tenant app's starting point.

**The non-negotiables from `about.html` that govern DC design:**
- Free forever — no paywalls, no premium tiers
- No ads, no promoted content, no sponsored listings
- No data tracking, no behavioral analytics
- Documents stay in the user's own cloud (Google Drive/Dropbox/OneDrive)
- Plain language, never jargon — tenant is often scared and short on time
- Clarity over cleverness — confused tenant = failed design

---

## 12. Open Questions — Resolved

| # | Question | Decision | Reason |
|---|----------|----------|--------|
| Q2 | When does OCR run? | Auto, on upload, in background | Already built in `upload/auto`. No change needed. |
| Q3 | How is doc type set? | Semptify suggests, tenant can override any time | Classifier already detects it. Pre-fill the dropdown. No modal confirmation step. |
| Q6 | Replace or alongside `/documents`? | Replace | `app/templates/pages/documents.html` is the canonical 3-pane DC shell. One URL, one purpose. |
| Q7 | DC URL? | `GET /documents` in `app/main.py` (with `GET /tenant` falling back to the same template) | Many UI links still hardcode `/tenant/documents`; should be reconciled with SSOT navigation in a separate refactor. |

---

## Pre-Build Checklist (before writing any code)

- [x] `app/core/overlay_types.py` — read. Types confirmed. `DOCUMENT_EXTRACTION`, `DOCUMENT_CLASSIFICATION`, `PARTY_EXTRACTION`, `TIMELINE_EXTRACTION`, `HIGHLIGHT`, `NOTE` all exist.
- [x] Read `app/core/navigation.py` — `tenant/documents` is not a named `FlowStage`; the DC page is served by `app/main.py` at `GET /documents` (with `GET /tenant` falling back to the same template). Navigation links use `/tenant/documents` hardcoded today; should be reconciled with SSOT later (separate refactor).
- [x] Read `app/sdk/vault/client.py` — no `get_file()` method; use `download(self, subfolder: str, filename: str) -> bytes` to fetch file bytes and `list_files(self, subfolder)` to list folder contents.
- [x] Read `app/templates/pages/documents.html` — no longer a stub; it is the full 3-pane Slice 1 shell (left vault list, center viewer frame, right overlays panel).
- [x] Confirmed `app/core/utc.py` exports `utc_now()` and `utc_now_iso()`.
- [x] Slice 1 is unblocked and implemented — see `app/modules/document_center/router.py`, `register.py`, `tests/test_dc_smoke.py`, and `app/templates/pages/documents.html`. No further hardcoded-data scaffolding needed.
