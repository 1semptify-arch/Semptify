# Page Composer Assembly Formula — Blueprint

**Status:** APPROVED — implemented
**Module path:** `app.modules.page_composer` (formula lives in `app/modules/page_composer/assembly.py`)
**Type:** Feature Module enhancement (CORE tier)
**Capability tier:** CORE
**Pillar span:** RECORD / KNOW / ACT / GOVERN

---

## 1. Problem it solves

Semptify already has three page-building pieces in flight:

- `app.modules.page_composer` — assembles JSON page views from Context Engine facts, tenant stories, and case data.
- `app.services.ui_composer` — turns user context into ordered component lists for `generic_page.html`.
- `app.modules.page_shell` — renders a validated `PageConfig` into a four-pillar grid of `InputBlock | InfoBlock | OutputBlock` blocks.

None of these currently share a single, explicit rule for *how* a user's situation becomes a page. The Page Composer Assembly Formula is that rule: a deterministic, auditable transform from `(user context, subject/intent, jurisdiction)` → a populated `PageConfig` that the Page Shell can render, while still feeding the legacy UI Composer component list where needed.

Without this formula, the three composers risk producing conflicting pages for the same user state.

## 2. Scope

### What it DOES do

- Define the canonical input set the Page Composer needs before it can assemble a page.
- Classify the situation into a `major_pillar`, a named `blend`, and four `channels` levels.
- Map existing data sources (Context Engine, Case Builder, Timeline, Calendar, Vault) into `PageShell` block kinds.
- Apply GOVERN floor/override rules *before* rendering, so a page can never under-state its risk.
- Emit both a `PageConfig` (for Page Shell) and a legacy component list (for `generic_page.html` / UI Composer) from one pass.
- Remain fully deterministic: same inputs always produce the same blocks, modulo upstream data changes.

### What it does NOT do

- It does not replace the Page Shell renderer; it feeds it.
- It does not invent facts — all facts keep their `source_url` from Context Engine.
- It does not perform its own layout/CSS — visual rendering stays in `page_shell`.
- It does not execute actions — `OutputBlock.on_trigger` is passed through to the frontend; the formula only decides *which* actions appear and *how prominent* they are.
- It does not bypass capability gates — users still only see blocks for modules they have access to.

## 3. Roles

| Role | Default access | Notes |
| --- | --- | --- |
| `tenant` | YES | Primary consumer; formula drives their dashboard, timeline, library, and subject pages. |
| `advocate` | YES | Can invoke formula on behalf of a linked tenant; same output shape. |
| `admin` | YES | Can introspect formula inputs/outputs for debugging. |
| `guest` | PARTIAL | Public preview endpoint omits user case data and personal actions. |

## 4. Database tables

No new tables. The formula reads existing sources and writes nothing to the database. Future audit logging may write to the existing `audit_log` table via `AuditHook`.

## 5. API endpoints

All endpoints live under the existing `app.modules.page_composer.router` prefix `/api/page`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/page/{subject}` | Assemble a page for a canonical subject (legacy JSON view). |
| GET | `/api/page/{subject}/preview` | Public preview of a subject page, no user case data. |
| GET | `/api/page/{subject}/config` | **NEW** Return the assembled `PageConfig` for Page Shell rendering. |
| GET | `/api/page/{subject}/render` | **NEW** Return the Page Shell HTML for the assembled config. |
| POST | `/api/page/assemble` | **NEW** Generic assembly endpoint: post `{user_id?, intent, subject?, jurisdiction, context?}` and receive `{page_config, html?, components?}`. |
| GET | `/api/page/` | List composable subjects (existing). |

## 6. Modules / services it calls

| Callee | Data provided |
| --- | --- |
| `app.services.context_loop` | User context (document count, deadlines, urgency, active case flags). |
| `app.modules.context_engine.cache` | Verified facts for `subject` + `jurisdiction`. |
| `app.modules.context_engine.stories` | Published tenant stories. |
| `app.modules.case_builder` | Active cases for the user filtered by subject. |
| `app.modules.calendar` | Upcoming deadlines/hearings. |
| `app.modules.timeline` | Recent events. |
| `app.modules.vault` | Document existence/count only (not content). |
| `app.modules.page_shell.loader` | Validate and clamp the generated `PageConfig`. |
| `app.modules.page_shell.renderer` | Render `PageConfig` to HTML. |
| `app.core.capabilities` | Filter blocks by user capability tier. |

## 7. The assembly formula

```text
Page = Assemble(UserContext, Subject, Jurisdiction, RequestedIntent)
```

### 7.1 Inputs

| Input | Source | Notes |
| --- | --- | --- |
| `user_id` | Cookie / auth gate | Optional for public preview. |
| `subject` | Path param or intent | One of the 13 `context_engine.taxonomy.Subject` values, or `null` for intent-only pages. |
| `jurisdiction` | Query param, default `MN` | Drives fact lookup and action availability. |
| `intent` | Query/body | `landing`, `timeline`, `library`, `documents`, `tools`, `workflow_step`, `subject_page`. |
| `context` | Context Loop | Document count, deadlines, case flags, role. |

### 7.2 Phase 1 — Classify

Compute the user's **intensity** (0-100) from Context Loop signals:

```text
intensity = max(
  deadline_proximity_score,   # 0-100, higher as nearest deadline approaches
  case_active_score,          # 0 or 70 if any open case
  document_count_score,       # 0-30 scaled by doc count
  eviction_notice_score,      # 0 or 90 if an eviction notice is detected
  hearing_scheduled_score,    # 0 or 80 if a hearing is on the calendar
)
```

The exact scoring function is hand-tunable in `assembly.py`; the formula only requires it stays monotonic and bounded 0-100.

From `subject` + `intent` + `intensity`, choose a `major_pillar`:

| Situation | `major_pillar` | Rationale |
| --- | --- | --- |
| New user, ≤1 doc, no urgency | `record` | First job is to start capturing evidence. |
| User browsing a subject with no active case | `know` | Library-style, facts-first. |
| Active case + upcoming deadline/hearing | `act` | User needs to do something now. |
| Active case + high risk (eviction, court date ≤ 7 days) | `govern` | Disclaimer and escalation must dominate. |
| Explicit `intent=timeline/documents` | `record` | User chose a RECORD pillar view. |
| Explicit `intent=library` | `know` | User chose a KNOW pillar view. |

### 7.3 Phase 2 — Select blend and channel levels

The blend is a named preset in `app.modules.page_shell.blends`. The formula picks the blend, then derives `ChannelLevels` from it. Channel levels can be *modified* by intensity but never beyond the blend's intent.

| `major_pillar` + intensity | Blend | Channels (record, know, act, govern) |
| --- | --- | --- |
| `record`, low intensity | `first_contact` | 70, 60, 15, 30 |
| `record`, high capture need | `quiet_capture` | 90, 10, 5, 25 |
| `know`, low intensity | `orientation` | 20, 80, 20, 20 |
| `act`, high urgency | `urgent_action` | 15, 25, 90, 70 |
| `act`, post-filing | `post_filing_calm` | 30, 40, 30, 50 |
| `govern`, high risk | `high_stakes_review` | 20, 30, 40, 90 |

### 7.4 Phase 3 — Gather blocks

For each pillar, pull candidate blocks from upstream modules.

#### RECORD → `InputBlock`

- `file_upload` — "Upload a document" (always present if `record` level > 0)
- `date` — "When did this happen?"
- `text` — "What happened?" (quick capture)
- `select` — capture type (conversation / notice / repair / payment / harassment / other)
- `signature` — only if a pending document requires signature

#### KNOW → `InfoBlock`

- One `InfoBlock` per verified fact from Context Engine cache.
- One collapsed `InfoBlock` per published tenant story (grouped under the first fact).
- Reading level defaults to `plain`; escalate to `intermediate` if the fact contains statutory citations.
- `content_ref` = the canonical fact/story ID so the renderer can load the full text.

#### ACT → `OutputBlock`

- `generate_letter` — if subject is repair/rent/lease/deposit
- `start_case` — if no active case exists for the subject
- `file_complaint` — if case exists and jurisdiction has a known agency path
- `contact_legal_aid` — if `govern` level ≥ 60
- `download_packet` — if documents + case exist
- `add_deadline` — if calendar module available

#### GOVERN → `OutputBlock` + `InfoBlock`

- Disclaimer `InfoBlock` — "Semptify is not a lawyer..." (always)
- Escalation `OutputBlock` — "Contact legal aid" when risk tier is high
- Data-privacy `InfoBlock` — storage-based auth reminder
- Override block — `suppresses_act_block` set to any ACT block that GOVERN rules must disable (e.g. suppress "file_complaint" if the deadline has passed and the case is time-barred).

### 7.5 Phase 4 — Apply capability filter

Drop any block whose `writes_to` or `on_trigger` target requires a module the user does not have. Keep a `dropped_blocks` list for the `govern_report`.

### 7.6 Phase 5 — Apply GOVERN rules

Pass the draft `PageConfig` through `app.modules.page_shell.govern.apply_govern_rules`:

1. Clamp GOVERN to the floor for the inferred risk tier.
2. Collect `suppresses_act_block` IDs from GOVERN blocks.
3. Remove suppressed ACT blocks from the ACT zone.
4. If the inferred risk tier is `very_high_do_not_build`, reject the page and return a safe fallback (GOVERN-only page with a legal-aid prompt).

### 7.7 Phase 6 — Output

The formula returns a `PageAssemblyResult`:

```python
{
  "page_config": PageConfig,           # for page_shell renderer
  "components": List[ComponentDict],   # legacy UI Composer component list
  "govern_report": dict,                # clamping, suppression, dropped blocks
  "metadata": {
    "subject": str | None,
    "jurisdiction": str,
    "major_pillar": str,
    "blend": str,
    "intensity": int,
    "risk_tier": str,
  }
}
```

`components` is a backward-compatible list so existing `generic_page.html` and HTMX fragments keep working while the four-pillar Page Shell is rolled out.

## 8. Data mapping reference

| Source data | Becomes | Block kind | Zone |
| --- | --- | --- | --- |
| Context Engine fact | InfoBlock | `info` | KNOW |
| Tenant story | InfoBlock (collapsed) | `info` | KNOW |
| Vault document count | Stat badge / empty state | `info` | RECORD |
| Calendar deadline | OutputBlock "Add to timeline" | `output` | ACT |
| Case Builder case | OutputBlock "Continue case" | `output` | ACT |
| Subject selection | Subject grid card | `info` | KNOW |
| File upload action | InputBlock | `input` | RECORD |
| Legal aid referral | OutputBlock | `output` | GOVERN |
| Disclaimer | InfoBlock | `info` | GOVERN |

## 9. Risk

| Risk | Mitigation |
| --- | --- |
| Different pages for the same user state | Formula is deterministic; all tunable weights live in one file and are versioned. |
| GOVERN under-weighted for high-risk cases | Floor rules in `page_shell.govern` clamp GOVERN before render; formula cannot override them. |
| Capabilities leak blocks to wrong role | Capability filter in Phase 4 gates every `OutputBlock` and `InputBlock`. |
| Upstream module unavailable | Each gatherer is wrapped in `try/except`; missing modules produce empty zones, not crashes. |
| Facts without `source_url` | `page_composer.service` already rejects/handles this; the formula only passes through verified facts. |
| Overly complex scoring | Intensity is a simple bounded max() of signals; no ML, no hidden state. |

## 10. Implementation notes

- The assembly formula is implemented in `app/modules/page_composer/assembly.py`.
- `PageAssemblyResult` is in `app/modules/page_composer/models.py`.
- The capability filter uses `block.module_name` (now present on `InputBlock`, `InfoBlock`, and `OutputBlock`) and compares it against `context["capabilities"]` (resolved module paths from `app.core.module_gate`).
- The capability-filter endpoints in `app/modules/page_composer/router.py`, `/gui/dashboard`, and `/gui/page/{subject}` pass resolved module paths into `assemble_page`.
- Case Builder integration is provided by `app/modules/case_builder/case_builder.py::get_cases_for_user`.
- Page Shell is a CORE dependency in `app/core/product_manifest.py`; its contracts are loaded by `app/core/contract_loader.py`.
- Mobile rendering is handled by the `max-width: 1024px` media query in `static/page_shell/page_shell.css`, which switches `.page-shell` to normal document flow (`height: auto; overflow: visible`).

## 11. Build order

1. Add `app/modules/page_composer/assembly.py` with the classification, blend selection, and block-gather functions.
2. Add `PageAssemblyResult` model to `app/modules/page_composer/models.py` (or a new `schemas.py`).
3. Wire the new `/api/page/{subject}/config` and `/api/page/{subject}/render` endpoints in `app/modules/page_composer/router.py`.
4. Update `app.modules.page_composer.register` `FunctionGroupContract` to document the new outputs (`page_config`, `components`).
5. Add unit tests covering each `major_pillar` branch and the GOVERN clamp/override paths.
6. Run `python -m py_compile` on changed files and `pytest` on the new tests.

## 11. Success criteria

- A request for `/api/page/eviction/config` with an active eviction case returns a `govern_focus` `PageConfig` with GOVERN ≥ 60.
- A request for `/api/page/repair/config` with no active case returns a `know_focus` or `record_focus` config, never `act_focus`.
- The same inputs always produce the same `PageConfig` blocks (order + IDs).
- Existing `/api/page/{subject}` JSON endpoint continues to return facts + stories + case data unchanged.
- All new files compile and pass lint.
