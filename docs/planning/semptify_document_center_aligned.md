# Semptify Document Center — Aligned Pipeline (as actually built)

This replaces the naming used in the earlier rough-draft doc. That draft was directionally useful for the *concepts* (color-coded highlighter, validation states, footnote traceability, single-source-of-truth principle) but used names that don't match the real codebase, and assumed some things exist that don't. This version is grounded in an actual repo audit.

---

## Pipeline as actually built

```
Upload → VAULT (SHA-256 + certificate + SEM ID)
            ↓
         LIGHT INTAKE (fast, synchronous: rough OCR, doc-type guess, user-supplied fields)
            ↓
         DOCUMENT / DocumentPipelineIndex / DocumentRegistry (master record created here)
            ↓
         [queued] DEEP OCR PIPELINE — own stage, decoupled from upload
            ↓
         UNIFIED OVERLAYS (highlight, note, footnote, tracked edit) — Deep OCR writes here
            ↓
         DOCUMENT CENTER (3-pane viewer + right-panel: real status, not a dead end)
            ↓
         RENT LEDGER (payments only — needs expansion for full ledger)
            ↓
         CALENDAR (calendar events, beta)
            ↓
         TIMELINE (aggregated chronological view)
            ↓
         CASE BUILDER / BRIEFCASE EXPORT (attorney intake packet / folder ZIP)
```

**Decision made: Deep OCR is its own pipeline stage, not folded into Intake.** Rationale — upload confirmation stays fast regardless of extraction load, urgent documents (eviction notices) can jump the queue ahead of routine correspondence, and documents can be reprocessed later (better OCR model, disputed extraction) without re-touching Light Intake or the Vault record at all.

### Deep OCR pipeline — design

**Precise mechanism — this matters for how agents build it:** Deep OCR is not a second character-recognition pass. It's **one OCR read, then one Semantic Context Engine pass on top of it.**

- **Pass 1 (Light Intake)**: raw OCR — text + bounding boxes + a rough, low-confidence guess at structure. This is mechanical: reading pixels, nothing more.
- **Pass 2 (Semantic Context Engine — this *is* what "Deep OCR" means here)**: takes pass 1's raw text as input, no re-scanning of the image. It matches against the tenancy domain schema (tenant/landlord/lease/notice/payment concepts), extracts the trigger phrase surrounding each date/entity candidate ("must respond by," "signed this ___ day of," "effective as of"), and uses that context to both classify the semantic role and raise the confidence score from pass 1's rough guess to a properly evidence-backed percentage. Cheaper than double-OCR, and meaningfully more accurate, since pass 2 has real context instead of guessing blind.

- **Trigger**: auto-queued immediately after Light Intake completes (default, non-blocking), with support for on-demand reprocessing (user opens a stale/failed document, or explicitly requests re-run).
- **Priority**: queue ordered by the urgency flag captured at Light Intake — an eviction notice should process ahead of a routine rent receipt sitting in the same queue.
- **Status field** (`deep_ocr_status`: `pending` / `processing` / `complete` / `failed` / `needs_reprocess`) lives on the Document/DocumentPipelineIndex record and is shown *honestly* in Document Center's right panel — replacing the current silent `processing_incomplete` dead end with a real, visible state the user understands ("still being processed" vs. "something's broken").
- **Output**: writes fully-tagged extraction results (date roles, trigger phrases, confidence, bounding boxes) via `UnifiedOverlayManager.create_overlay()` — this is where the previously-missing bridge gets built, but now as a natural consequence of Deep OCR being its own stage with its own defined output contract, not a bolt-on fix to Intake's existing code path.
- **Failure handling**: a failed Deep OCR run shouldn't block the document from existing in the Vault/Ledger/Docket record — Light Intake already made it visible and usable at a basic level; Deep OCR failing just means the highlighter/overlay layer isn't populated yet, and the status field should say so plainly.

### Build order for this specific piece (one task per commit)

1. Add `deep_ocr_status` field to the Document/DocumentPipelineIndex model.
2. Build Deep OCR as its own decoupled service/queue — not a function call inside Intake's synchronous path.
3. Queue prioritization logic keyed off the urgency flag from Light Intake.
4. Deep OCR job writes results via `UnifiedOverlayManager.create_overlay()` on completion.
5. Update Document Center's right panel to surface real `deep_ocr_status` instead of the generic incomplete state.
6. On-demand reprocess/re-run endpoint, callable per document.

---

## Terminology correction — old draft name → real module

| Old draft term | Real module | Status |
|---|---|---|
| Vault | `vault_upload_service.py`, upload via `POST /api/intake/upload/auto` (UI-facing) — vault's own `POST /upload` is internal | Core / stable |
| "Notarized" / integrity seal | SHA-256 + self-signed JSON certificate + DocumentRegistry SEM ID. **Not blockchain.** RFC 3161 TSA exists but only used by `legal_integrity.py` | Partial |
| Docket (master record) | **Doesn't exist and shouldn't be built** — use `Document` + `DocumentPipelineIndex` + `DocumentRegistry`, which already do this job | Do not build |
| Journal (free-form narrative) | **Doesn't exist yet.** Current "journal" (`JournalEntry`/`JournalSummary` in `tenant_briefcase.py`) is auto-generated from vault uploads, not user-editable. `/tenant/journal` redirects to `/tenant/home`. Listed in `ACTIVE_CONTEXT.md` as not yet built | Needs new module |
| Briefcase (deep OCR + highlighter + notes) | Real Briefcase (`briefcase/router.py`) is an **in-memory** folder/annotation organizer — tags, highlights, notes, ZIP export. Deep OCR/extraction actually lives in **Intake** + `unified_overlay_manager.py`, not Briefcase | Partial, and in-memory (not persisted) |
| Account Ledger | Real module exists (`rent/router.py` + `RentPayment` model) but only tracks paid/late/partial/missed rent payments | Partial — needs real expansion |
| Calendar | Real (`calendar/router.py`, `CalendarEvent` model, `calendar_from_documents` contract) but does **not** auto-populate from every vault item by default | DEV / beta |
| Timeline | Real and solid — aggregates documents, calendar, vault, rent payments, cloud events, with multiple time axes (event_time/record_time/entry_time) | Core |
| Packet Builder | No unified version exists. `case_builder` has attorney intake-packet endpoints (`/cases/{case_id}/intake-packet`, `/pdf`, `/zip`); Briefcase has a `court_packets` folder + `/export` ZIP. A `COURT_PACKET_QUERY` overlay type exists but isn't implemented | Split across two places, not unified |

---

## Real gaps, ranked by what actually blocks progress

1. **Deep OCR needs to be built as its own decoupled stage** (see design above) — this replaces the earlier "just fix the Intake bridge" framing. It's more work than a one-line fix, but it's the right foundation: fast uploads, priority queuing for urgent documents, and reprocessing without touching Light Intake.
2. **Journal module doesn't exist as a user-facing feature.** Needs a real `app/modules/journal` — model, endpoints, UI — if free-form tenant narrative is actually wanted. This is a from-scratch build, already flagged in your own `ACTIVE_CONTEXT.md`. **Confirmed use case:** logging a verbal conversation the tenant had (e.g., a hallway exchange with the landlord) as a contemporaneous, timestamped record — this makes Journal entries themselves a form of evidence, not just casual notes, so they likely want the same timestamp/integrity treatment as uploaded documents, not a lighter-weight text field.
3. **Account Ledger needs real expansion.** Currently payment-status tracking only. Missing: fee types beyond late fees, deposits, credits, running balance, period-covered field, source attribution (OCR-extracted vs. manually entered), and links to overlay highlights. This is the gap between "rent tracker" and the full $ module discussed earlier.
4. **Packet Builder needs unification.** Right now it's two separate things (attorney intake packet in `case_builder`, folder ZIP export in Briefcase). If the goal is one coherent "curate documents + highlights + notes + footnotes → export" feature, that's new integration work, not a rename.
5. **Calendar isn't a pure projection yet.** It stores its own `CalendarEvent` rows rather than automatically reflecting every vault item; the auto-sync contract (`calendar_from_documents`) exists but isn't the default behavior.
6. **Briefcase persistence.** Being in-memory is a real risk for something meant to hold evidence — annotations/highlights need to survive a restart, not live only in session memory.
7. **TSA timestamp isn't wired into the standard certificate.** If trusted third-party timestamping (not blockchain, but a real independent timestamp authority) is something you want on every upload rather than only through `legal_integrity.py`, that's a specific, scoped wiring task.

---

## Integrity model decision: self-signed cert vs. TSA vs. blockchain

Three real options, ranked by what they actually prove:

| Approach | What it proves | Cost/complexity | Status |
|---|---|---|---|
| Self-signed cert (current default) | File unaltered since cert creation. Does **not** independently prove Semptify itself didn't fabricate the timestamp | Free, already built | Live |
| RFC 3161 TSA (already in codebase, not wired to every upload) | Independent third party attests to the timestamp — Semptify can't have faked it. Legally recognized standard (eIDAS, various US contexts) | Free/near-free (e.g. FreeTSA), client already exists | **Recommended near-term fix** — just needs wiring into every vault upload |
| Blockchain anchoring | Publicly, permanently verifiable, independent of Semptify's existence — strongest possible tamper-proof claim | Real infra to build/maintain: wallet/key management, chain choice, confirmation delays; cheap only via batch-anchoring (e.g. OpenTimestamps-style Merkle batching to Bitcoin) rather than per-document transactions | Not built — would be new work |

**Recommendation:** wire TSA into the standard upload path first — it directly answers the "could Semptify have faked this" question, using code that already exists. Treat blockchain anchoring as a possible later addition on top of TSA (not a replacement), if the goal is specifically a "publicly verifiable forever, independent of Semptify existing at all" story for legal credibility or fundraising — and if pursued, batch-anchoring is the only realistic cost model at Semptify's scale.

---

## What still holds from the earlier draft (concepts, not names)

- Color-coded highlighter with a single shared legend, reused everywhere it appears.
- Validation states (unconfirmed/confirmed/corrected/rejected) gating what counts as an established fact — this still needs to land in **Unified Overlays**, not a separate "Briefcase deep OCR" that doesn't actually exist that way.
- Footnotes as structural citations back to exact document location — same principle, lands in Unified Overlays.
- Single-source-of-truth discipline: Document/DocumentPipelineIndex/DocumentRegistry as the one master record; Calendar and Timeline as projections over it, not their own stores (Timeline already does this correctly; Calendar doesn't yet).
- Account Ledger as a real data store (not a pure projection), since cash payments have no document to extract from — this still holds, it just needs to be built out from the existing `RentPayment` model rather than invented fresh.

---

## Suggested next step

Fix #1 (Intake → Overlay bridge) before touching anything else in this list — it's the dependency everything else in the Document Center vision sits on top of. Once that's wired, the highlighter/validation/legend work becomes "finish what's connected" rather than "build on a gap."
