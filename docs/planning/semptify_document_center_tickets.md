# Document Center — Task Tickets for Orchestrator Queue
Generated from `semptify_document_center_aligned.md`. One task per commit, per your standing process rules. Each ticket lists what to preflight-read before starting and what NOT to touch.

---

## TICKET 1 — Add `deep_ocr_status` field
**Goal:** Add a status field to the master document record to track Deep OCR pipeline state.
**Preflight read:** `app/models/models.py` (Document / DocumentPipelineIndex definitions), `app/services/document_registry.py`.
**Scope:** Add field only — `deep_ocr_status`: enum (`pending` / `processing` / `complete` / `failed` / `needs_reprocess`). Default `pending` on creation.
**Do not touch:** Vault upload logic, certificate generation, Intake's existing OCR call.
**Acceptance:** Field exists on the model, migrates cleanly, defaults correctly on new document creation. No behavior change yet — nothing reads or writes it besides the default.

---

## TICKET 2 — Decouple Deep OCR into its own queued service
**Goal:** Move the extraction step out of Intake's synchronous path into its own background service/queue.
**Preflight read:** `app/modules/intake/router.py`, existing OCR call inside it (reuse this — do not rewrite OCR itself), whatever job/queue infrastructure already exists in the repo (check before introducing a new one).
**Scope:** Pass 1 (raw OCR + bounding boxes) stays exactly as it is inside Light Intake — no changes to the actual OCR call. New: a separate queued job that picks up documents in `pending` status and runs them through pass 2 (see Ticket 4). This ticket is just the plumbing — queue exists, picks up jobs, updates status to `processing` — pass 2 logic itself is Ticket 4.
**Do not touch:** Intake's existing rough OCR call — reuse its output, don't duplicate it.
**Acceptance:** A document uploaded through normal flow gets picked up by the new queue and its `deep_ocr_status` flips to `processing`. Pass 2 logic can be a stub/no-op for this ticket.

---

## TICKET 3 — Queue priority by urgency flag
**Goal:** Documents flagged urgent at intake jump ahead of routine documents in the Deep OCR queue.
**Preflight read:** Ticket 2's queue implementation, the urgency field captured at Light Intake.
**Scope:** Add priority ordering to the queue consumer — urgent-flagged documents processed first.
**Acceptance:** Two documents queued back-to-back, one flagged urgent after the other — urgent one processes first regardless of upload order.

---

## TICKET 4 — Semantic Context Engine (pass 2 logic)
**Goal:** Implement the actual reasoning layer — takes pass 1's raw OCR text as input (no re-scanning images), classifies date/entity roles using domain schema + trigger-phrase matching, outputs confidence-scored results.
**Preflight read:** Ticket 2's queue plumbing, the tenancy domain schema/date-role categories already defined (Category A intrinsic dates: created, signed, issued, effective, claimed-service, deadline, period).
**Scope:** Given raw OCR text input, output a structured list of `{raw_text, semantic_label, trigger_phrase, confidence, bounding_box}` objects. Rule-based/regex pass for common patterns first; fall back to a single LLM call only for ambiguous cases, not every field.
**Do not touch:** Pass 1 OCR, the queue plumbing from Ticket 2 (only the logic that runs inside a queued job).
**Acceptance:** Given a test document, produces correctly labeled, confidence-scored date objects with trigger phrases attached.

---

## TICKET 5 — Wire pass 2 output to `UnifiedOverlayManager.create_overlay()`
**Goal:** Fix the missing bridge — pass 2's output actually reaches the overlay system.
**Preflight read:** `unified_overlay_manager.py`, `create_overlay()` signature, `document_center/router.py` (to confirm what it expects to read).
**Scope:** On pass 2 completion, call `create_overlay()` with the structured results from Ticket 4. Update `deep_ocr_status` to `complete` (or `failed` on error).
**Acceptance:** Document Center's right panel stops returning `processing_incomplete` for a fully processed document — real overlay data is present and readable.

---

## TICKET 6 — Document Center right panel: honest status display
**Goal:** Replace the generic incomplete state with the real `deep_ocr_status`.
**Preflight read:** `document_center/router.py` right-panel logic.
**Scope:** Display `pending` / `processing` / `complete` / `failed` / `needs_reprocess` distinctly to the user — "still processing" vs. "something went wrong" are different messages.
**Acceptance:** A user opening a document mid-processing sees an honest, non-alarming status instead of an ambiguous incomplete state.

---

## TICKET 7 — On-demand reprocess endpoint
**Goal:** Allow re-running Deep OCR on a specific document without touching Vault/Light Intake.
**Preflight read:** Tickets 2, 4, 5.
**Scope:** New endpoint — re-queues a document for pass 2, resets `deep_ocr_status` to `pending`.
**Acceptance:** Calling the endpoint on a `complete` or `failed` document re-triggers pass 2 and updates status accordingly.

---

## TICKET 8 — Wire RFC 3161 TSA into standard vault certificate
**Goal:** Every vault upload gets an independent, third-party timestamp — not just uploads processed through `legal_integrity.py`.
**Preflight read:** `tsa.py`, `vault_upload_service._create_certificate`, `legal_integrity.py` (to see current TSA usage pattern).
**Scope:** Call the existing TSA client from the standard certificate creation path. No new TSA client needed — reuse what exists.
**Do not touch:** DocumentRegistry ID generation, SHA-256 hashing logic itself.
**Acceptance:** A normal vault upload's certificate now includes a valid RFC 3161 timestamp token, verifiable independently of Semptify.

---

## TICKET 9 — Journal module (new)
**Goal:** Build real free-form tenant narrative capture — confirmed use case: logging a verbal conversation (e.g., hallway exchange with landlord) as a contemporaneous record.
**Preflight read:** `ACTIVE_CONTEXT.md` (Journal listed as not-yet-built), current `JournalEntry`/`JournalSummary` in `tenant_briefcase.py` (auto-generated, different from what's being built — do not conflate).
**Scope:** New `app/modules/journal` — model, create/read endpoints, basic UI. Each entry: free text, timestamp, optional link to a related document. Since entries may function as evidence, apply the same integrity treatment as documents (timestamp via Ticket 8's TSA path once available).
**Do not touch:** Existing auto-generated journal summary logic — this is additive, a new user-facing capability, not a replacement.
**Acceptance:** A tenant can create a free-text journal entry with a timestamp, unrelated to any document upload, and retrieve it later.

---

## TICKET 10 — Account Ledger expansion
**Goal:** Expand `RentPayment`-based tracker into a full ledger.
**Preflight read:** `rent/router.py`, `RentPayment` model.
**Scope:** Add entry types beyond payment status (fees, deposits, credits), `period_covered`, `source` (`ocr_extracted` / `user_entered`), running balance calculation, and a link field to the relevant overlay highlight when an entry originates from a document.
**Acceptance:** A ledger entry can be created manually (no document) or linked to a specific highlighted amount in a processed document; running balance calculates correctly across multiple entries.

---

## TICKET 11 — Calendar: real projection from vault items
**Goal:** Calendar auto-populates from documents/deadlines instead of only manually-created `CalendarEvent` rows.
**Preflight read:** `calendar/router.py`, `calendar_from_documents` contract (exists but not default behavior).
**Scope:** Wire the existing contract so it actually runs by default — confirmed deadlines and vault items appear on Calendar without a separate manual event-creation step.
**Acceptance:** Uploading and confirming a document with a deadline causes it to appear on Calendar automatically, no manual event entry required.

---

## TICKET 12 — Packet Builder unification
**Goal:** One coherent curated-export feature instead of two separate ones (`case_builder` attorney packets, Briefcase ZIP export).
**Preflight read:** `case_builder/router.py` (intake-packet/pdf/zip endpoints), `briefcase/router.py` (court_packets folder, export), `overlay_types.py` (`COURT_PACKET_QUERY` — exists but unimplemented).
**Scope:** Design decision needed before coding starts — merge into one endpoint/UI that pulls documents + highlights + notes + footnotes into a virtual folder and exports (PDF and/or ZIP). **Flag for Brad's input before starting: overlay-preserved export vs. clean-copy-plus-summary, or both (see open item in aligned doc).**
**Acceptance:** TBD pending that decision — do not start coding until export format is confirmed.

---

## Suggested execution order
1 → 2 → 4 → 5 → 6 (this chain is the whole Deep OCR + overlay bridge, do it in order)
3 and 7 can slot in anytime after 2
8 is independent, can run in parallel with the above
9, 10, 11 are independent of each other and of the Deep OCR chain
12 needs your decision before any agent starts it
