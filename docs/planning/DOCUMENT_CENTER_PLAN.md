# Document Center — Canonical Plan

> Source: User vision, 2026-06-27
> Purpose: Reusable brief for AI sessions — paste this instead of re-explaining

## Naming

- **DC** = Document Center (the page)
- One page for all documents AND all overlays — no fragmentation

## The 5 Actions (Document Center UI)

1. **Upload** — tenant adds a document
2. **Store** — saved to vault
3. **Process** — OCR + AI extraction
4. **Review** — tenant + Semptify verify data together (the core innovation)
5. **Share** — tenant chooses who sees it

## DC Layout (desktop GUI, 3-pane)

```
+----------------+--------------------------------+-------------------+
|  Vault List    |  Semptify Viewer               |  Overlays Panel   |
|  (left)        |  (center, selected doc)        |  (right)          |
|                |                                |                   |
|  - doc1.pdf    |  +-- viewer frame ---------+   |  Process: OCR     |
|  - doc2.pdf    |  | [top bar: item options] |   |  [====    ] 55%   |
|  - lease.pdf   |  |                          |   |                   |
|  - notice.pdf  |  |  document renders here   |   |  Process: Parties |
|  - ...         |  |  user + Semptify         |   |  [======  ] 80%   |
|                |  |  walk through together   |   |                   |
|                |  |                          |   |  Process: Dates   |
|                |  |  highlights, notes,      |   |  [===     ] 40%   |
|                |  |  references visible      |   |                   |
|                |  +--------------------------+   |  Goal: Verified   |
|                |                                |  [========] 90%   |
+----------------+--------------------------------+-------------------+
```

- **Left pane:** list of documents in vault
- **Center pane:** Semptify Viewer — selected document opens here
- **Right pane:** list of document-process overlays, each with completion % toward its original goal
- **Top of viewer frame:** options for the selected item

## Semptify Viewer (the Review step)

- Open the stored document inside a Semptify viewer (not a plain file list)
- User and Semptify walk through the document together in real time
- User watches the document being processed by Semptify (not a hidden background job)
- Semptify highlights and gathers key info:
  - Dates
  - Addresses
  - Party information (landlord, tenant, witnesses)
  - Contacts (phone, email)
  - Amounts (rent, deposit, fees)
  - Any other OCR-extractable fields
- OCR does the heavy lifting; user confirms or corrects
- Collaborative verification — not black-box AI

## Viewer Tools (top bar + inline)

- **Highlights** — mark text regions in the document
- **Notes** — attach notes to highlighted regions
- **References** — link a region to another document or a contact
- **User key system** — all highlights/notes/references tied to the user's key (like the Briefcase was supposed to be)
- These annotations ARE overlays — they show up in the right panel with completion %

## The Unlock Pattern (key behavior)

A document starts with just the viewer + basic overlays. As verified metadata accumulates in the overlays, new things unlock:

- Enough verified metadata → **Timeline view** unlocks
- More verified metadata → **Journal** unlocks
- Party/contact metadata verified → **Tenant Contact Manager** unlocks
- More → case builder, legal prep, etc. (future)

This is the gate system: overlays fill up → completion % rises → features unlock.
Tenant sees the progress bar fill and understands WHY something unlocked.

## Why This Design

- **Simplifies GUI massively** — 5 verbs, one viewer, no feature sprawl
- **Tenant sees what Semptify sees** — builds trust, calm UX
- **Collaborative verification** — tenant stays in control, AI assists
- **Structured output** — verified data flows into timeline, journal, case builder cleanly
- **Aligns with Semptify mission** — RECORD pillar; document everything, verified not just stored
- **Progressive unlock** — tenant isn't overwhelmed; features appear as they earn them
- **Desktop GUI first** — mobile later

## Per-Document-Type Required Fields

Each document type has a checklist of required fields. A document only passes as **verified/official** for its stated type when all required fields are confirmed by the user.

### Example: Lease Agreement
- [ ] Landlord full name
- [ ] Tenant full name
- [ ] Property address
- [ ] Lease start date
- [ ] Lease end date
- [ ] Rent amount
- [ ] Security deposit
- [ ] Signatures present

### Example: Notice to Vacate
- [ ] Sender name
- [ ] Recipient name
- [ ] Date of notice
- [ ] Vacate date
- [ ] Property address
- [ ] Delivery method

### Example: Repair Request
- [ ] Date submitted
- [ ] Issue description
- [ ] Property address
- [ ] Landlord/contact notified
- [ ] Response deadline

## Verification States

- **Unverified** — stored, no checklist review yet
- **In Review** — user + Semptify working through it
- **Verified** — all required fields for the stated type confirmed
- **Mismatched** — stated type doesn't match content (e.g., called a lease but missing signatures)

Unverified docs are still stored safely — they just don't feed into timeline/journal/case until reviewed.

## Why This Design

- **Simplifies GUI massively** — 5 verbs, one viewer, no feature sprawl
- **Tenant sees what Semptify sees** — builds trust, calm UX
- **Collaborative verification** — tenant stays in control, AI assists
- **Structured output** — verified data flows into timeline, journal, case builder cleanly
- **Aligns with Semptify mission** — RECORD pillar; document everything, verified not just stored

## Non-Goals (do NOT build these)

- Not a black-box "AI analyzed your doc" magic box
- Not auto-filing court documents from uploads
- Not sharing without explicit tenant action
- Not multiple competing viewers / fragmented UI

## Open Questions (resolved during implementation)

- [x] **Which document types get checklists first?** — `lease`, `notice_to_vacate`, `repair_request`, `rent_receipt`, `move_in_inspection` (plus `court_summons`, `correspondence`, `other` for completeness). See `app/modules/document_center/router.py` `ALLOWED_DOCUMENT_TYPES`.
- [x] **Where does the viewer render?** — PDF.js inline for `.pdf`; `<img>` for `.jpg`/`.png`/`.webp`; server-side conversion to PDF for `.docx`; sandboxed `<iframe>` for `.html`; `<pre>` for `.txt`. See `DC_DESIGN_SONNET.md` §3a.
- [x] **Does "Process" run automatically on upload, or on first Review open?** — Automatically on upload, in the background, via `POST /api/intake/upload/auto`.
- [x] **Should Semptify suggest the document type, or does tenant declare it?** — Semptify suggests via the intake classifier; tenant can override from the viewer dropdown at any time.
