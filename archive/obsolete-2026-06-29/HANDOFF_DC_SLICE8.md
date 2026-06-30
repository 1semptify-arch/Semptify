# Document Center — Handoff to Next Agent (Slice 8 → stable)
**Date:** 2026-06-28 | **Current state:** `beta` | **Target:** `stable`

---

## Current State

- **Lifecycle:** `beta` (admin-only)  
- **Forge tests:** 26/26 passing  
- **Contracts:** 5 registered  
- **All inline CSS extracted** — no linter warnings  

### Files you will touch
| File | Purpose |
|---|---|
| `app/modules/document_center/router.py` | Backend endpoints + `_synthesize_overlays` |
| `app/modules/document_center/register.py` | FunctionGroupContracts |
| `app/modules/document_center/tests/test_dc_smoke.py` | All Forge tests |
| `app/templates/pages/documents.html` | Full 3-pane UI + all JS |
| `app/core/product_manifest.py` | Lifecycle field (change to `stable`) |
| `BUILD_STATE.md` | Add session entry at top |

---

## Slice 8 — Formatted Drill-Down Display

### What to build

In `openOverlay()` (in `documents.html`, around line 1162), the current code renders `items` as raw strings. Format each overlay type distinctly:

| `overlay_type` | Format |
|---|---|
| `upload_notarization` | Show as `<code>SEM-2026-000001-ABCD</code>` certificate label |
| `document_classification` | Show as a pill badge: `<span class="dc-pill">Lease Agreement</span>` |
| `key_date_extraction` | One item per line, prefix icon 📅, no truncation |
| `party_extraction` | One item per line, prefix icon 👤, no truncation |
| `amount_extraction` | One item per line, prefix icon 💰, no truncation |
| `ocr_result` | Monospaced excerpt, italic, truncated at 200 chars already |

### CSS classes to add (inside `<style>` block in documents.html)
```css
.dc-pill {
    display: inline-block;
    background: rgba(108,158,248,0.15);
    color: var(--color-accent, #6c9ef8);
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 500;
}
.dc-expand-icon { margin-right: 4px; }
```

### JS change — replace the `openOverlay` innerHTML builder

Find the current block in `openOverlay()`:
```js
expandDiv.innerHTML = rawItems
  .map(item => `<div class="dc-overlay-expand-item">${String(item).substring(0, 140)}</div>`)
  .join('');
```

Replace with a formatter function:
```js
function _formatExpandItems(overlayType, rawItems) {
  if (rawItems.length === 0) {
    return '<div class="dc-overlay-expand-empty">No data extracted yet</div>';
  }
  const icon = {
    upload_notarization: '',
    document_classification: '',
    key_date_extraction: '📅 ',
    party_extraction: '👤 ',
    amount_extraction: '💰 ',
    ocr_result: '',
  }[overlayType] || '';

  if (overlayType === 'upload_notarization') {
    return `<code class="dc-overlay-expand-item">${rawItems[0]}</code>`;
  }
  if (overlayType === 'document_classification') {
    return `<span class="dc-pill">${rawItems[0]}</span>`;
  }
  return rawItems
    .map(item => `<div class="dc-overlay-expand-item"><span class="dc-expand-icon">${icon}</span>${String(item)}</div>`)
    .join('');
}

// Use it:
expandDiv.innerHTML = _formatExpandItems(overlayType, rawItems);
```

---

## Slice 8 Tests to Add

In `test_dc_smoke.py`, add after the existing `items` tests:

```python
def test_dc_synthesize_overlays_ocr_excerpt_capped():
    """OCR text excerpt is capped at 200 chars + ellipsis."""
    from app.modules.document_center.router import _synthesize_overlays
    from unittest.mock import MagicMock
    doc = MagicMock()
    doc.registry_id = None
    doc.document_type = None
    doc.processed = True
    doc.extracted_data = {"text": "A" * 500}
    doc.integrity_status = None
    result = _synthesize_overlays(doc)
    ocr = next(o for o in result["overlays"] if o["overlay_type"] == "ocr_result")
    assert len(ocr["items"][0]) <= 204  # 200 + "…" (3 bytes) + margin
    assert ocr["items"][0].endswith("…")

def test_dc_synthesize_overlays_items_capped_at_10():
    """items lists are capped at 10 entries."""
    from app.modules.document_center.router import _synthesize_overlays
    from unittest.mock import MagicMock
    doc = MagicMock()
    doc.registry_id = None
    doc.document_type = None
    doc.processed = True
    doc.extracted_data = {
        "dates": [f"2026-01-{i:02d}" for i in range(1, 20)],
        "parties": [f"Party {i}" for i in range(15)],
        "amounts": [],
    }
    doc.integrity_status = None
    result = _synthesize_overlays(doc)
    by_type = {o["overlay_type"]: o for o in result["overlays"]}
    assert len(by_type["key_date_extraction"]["items"]) <= 10
    assert len(by_type["party_extraction"]["items"]) <= 10
```

---

## How to Promote to `stable`

1. Run tests: `.\venv311\Scripts\python.exe -m pytest app/modules/document_center/tests/ -q --no-header --tb=short`
2. All pass → edit `app/core/product_manifest.py`:
   - Change `lifecycle="beta"` → `lifecycle="stable"`  
   - Update `dev_notes` last line
   - Update `log_message`
3. Update `BUILD_STATE.md` with session entry
4. Commit: `git add ... && git commit -m "feat(dc): Slice 8 — formatted drill-down, promoted to stable"`
5. Push: `git push origin main`

---

## Mandatory Pre-Flight (do this FIRST)

```powershell
# 1. Read these files before touching anything
Get-Content BUILD_STATE.md | Select-Object -First 60
Get-Content ACTIVE_CONTEXT.md

# 2. Activate correct Python
.\\venv311\\Scripts\\Activate.ps1
python --version  # Must be 3.11.9

# 3. Compile check
python -m py_compile app/modules/document_center/router.py
python -m py_compile app/modules/document_center/register.py

# 4. Run tests
.\\venv311\\Scripts\\python.exe -m pytest app/modules/document_center/tests/ -q --no-header --tb=short
```

---

## Architecture Rules (DO NOT VIOLATE)

- **Never** use `datetime.now()` — use `utc_now()` from `app.core.utc`
- **Never** use bare `except:` — always `except SpecificError:`
- **Never** create `_v2` or `_new` files — rewrite in place (ask user to rename original first)
- **Never** add cloud I/O to the `/overlays` endpoint — it must stay pure in-memory
- **Never** add `<script>` inline styles — all CSS goes in the `<style>` block
- Python **3.11.9 only** — no 3.12+ features

---

## User Manual — Document Center (admin preview)

### Accessing the Document Center
- Navigate to `/documents` while logged in as admin
- The page shows a 3-pane layout: **Documents** (left) · **Viewer** (center) · **Overlays** (right)

### Left Pane — Document List
- Lists all vault documents for your account
- Click any document row to open it
- Filter buttons at top: All · Certified · Processed · Unclassified

### Center Pane — Viewer
- **PDF/images** render inline in the iframe
- Other formats (`.docx`, `.zip`) show a download link
- **Document Type** dropdown lets you classify the document — saves immediately to DB

### Right Pane — Overlays
- Shows 6 processing progress bars: Certified Upload · Document Type · Text Extraction · Dates · Parties · Amounts
- Click **Open ▾** on any row to drill down and see the raw extracted values
- **Overall Verified** score is the average across all 6 items
- **Features** section shows which Semptify modules are unlocked based on your document scores

### Feature Unlock Thresholds
| Feature | Requirement |
|---|---|
| Timeline | 1 doc with Dates + Parties avg ≥ 80% |
| Journal | 2+ docs with overall score ≥ 60% |
| Contact Manager | Any doc with Parties = 100% |
| Case Builder | 3+ docs with overall score ≥ 80% |

### API Endpoints (admin only)
| Method | Path | Description |
|---|---|---|
| GET | `/api/dc/list` | All vault docs for current user |
| GET | `/api/dc/document/{id}/view` | Stream doc bytes inline (cookie auth) |
| GET | `/api/dc/document/{id}/overlays` | Synthesized overlay progress (no cloud I/O) |
| POST | `/api/dc/document/{id}/type` | Set/clear document type |
| GET | `/api/dc/unlocks` | Compute feature unlock state across all docs |
