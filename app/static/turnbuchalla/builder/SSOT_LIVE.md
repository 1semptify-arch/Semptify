# SSOT (LIVE) — how this folder builds

*The single source of truth for PROCESS. Design calls live in
`DECISIONS.md`, open work in `TASKS.md` — this file is the build guide:
how a piece of the project moves from idea to published. It is itself a
live doc — it grows in place and is never forked into dated copies.
Established 2026-10-19, per Brad.*

## The one rule underneath everything

**One canonical version per thing, kept live — and every change
propagates.** When a live doc changes, everything derived from it changes
in the same stroke: names, numbers, the funding model, statutory language,
the pitch. No stale copy survives a change. Derived artifacts that can't
auto-update (`.docx`, the `SHARE/` set, anything already sent) get
regenerated or explicitly flagged stale in the same session — never
"we'll fix it later."

## Canonical map — where each truth lives

| Thing | Canonical source | What derives from it |
|-------|------------------|----------------------|
| Statute text + drafting questions | `BILL_LIVE.md` | skeleton bill section of the outreach kit (frozen 10/16) |
| The show-piece / published thesis | `CONCEPT_SHEET_LIVE.md` | `CONCEPT_SHEET_LIVE.docx` + the `SHARE/` copies — regenerate on every accepted edit |
| Locked design decisions | `DECISIONS.md` | everything — a doc contradicting it is wrong, not the row |
| Open work | `TASKS.md` | Send Center queue |
| People, pitch status, resolved addresses | `CONTACTS.md` | the kit emails' To: fields |
| New dictated input | `NOTES_LIVE.md` | routes into the above, only on Brad's "merge it" |
| Release pipeline | `01_CONTENT/` → `02_APPROVING/` → `03_PUBLISHED/` | stage folders hold derivatives, never masters |
| Frozen research + drafts | `SOURCES/` → `01_Court_Cases/_Drafts_Work_Product/` | never edited — superseded lines get reconciled in the NEXT live version |
| What the outside world sees | `SHARE/` (`share.semptify.org/bill/`) | rebuilt from live docs at publish time only |

## The three stages — physical folders, not just policy

Stage = folder. **Live docs stay at root forever** — the dashboard,
link engine, and portal hardcode root paths, so a master that moves is
a master that breaks tools. What flows through the folders is the
DERIVATIVE: the `.docx` build, an email draft, a packet — the thing
headed outside.

| Folder | Stage | What sits here |
|--------|-------|----------------|
| `01_CONTENT/` | content | item drafts — sections, emails, pieces being shaped before they merge into a live doc |
| `02_APPROVING/` | approving | built artifacts awaiting Brad's word — **stale the moment its source doc changes; rebuild, don't patch** |
| `03_PUBLISHED/` | published | dated frozen releases — `YYYY-MM-DD_<thing>/`, never edited |
| `SHARE/` | published (live window) | the current public set at `share.semptify.org/bill/` — path hardcoded in `ops_console.py`, **do not move/rename** |

Publish is two moves in one stroke: dated copy into `03_PUBLISHED/` +
`SHARE/` refresh. Approving means Brad's explicit word — "approved,"
"merge it," or he clicks send. Nothing advances without it, not even
good text. Raw dictation lands in `NOTES_LIVE.md` at root, then gets
worked into shape inside `01_CONTENT/`.

## Standing rules (carried + confirmed)

- **Facts before reach** — a claim that can't survive fact-check doesn't
  ship. The standard: source + date + what it actually says (Jetty check
  10/18 is the model).
- **No sales language** — the math is the pitch.
- **Case = exhibit only if asked** (locked 10/14).
- **Bipartisan frame** — consumer protection on the left, court-cost
  savings on the right.
- **Sends go through Send Center — Brad clicks.**
- **Dated docs stay frozen; live docs live here.**
- **CHANGELOG gets a line per work session** (case-file protocol).
- **Fact-check ×3 before anything leaves** (Brad, 10/19) — every
  external-facing claim gets three passes: automated scan, source-vs-
  claim check, read-it-like-a-stranger. Nothing ships on one pass.
- **Research is the majority of the project** (Brad, 10/19) — research
  outputs are first-class `01_CONTENT/` pieces, not pre-work.
- **The frame: an alternative to a broken road** (Brad, 10/19) — the
  project answers a documented-broken system; the road we're on is the
  exhibit, not the pitch.

## What's been done under these rules

- 10/16 — naming locked (statute / Turnbuchalla / Semptify) → propagated
  to live concept sheet, `.docx`, and `SHARE/`.
- 10/18 — funding model resolved (deposit escrow + M1PR) → live in
  `BILL_LIVE` + `DECISIONS`; the frozen white paper's tenant-premium line
  flagged for reconcile in the next live version.
- 10/18 — third coverage leg (belongings insurance) → locked clause 8 in
  `BILL_LIVE`, row in `DECISIONS`.
- 10/18 — Jetty claim fact-checked → verified; ships in the show-piece.
- 10/18 — `SHARE/` seeded → published behind the bill link.
- 10/19 — folder skeleton completed → `SOURCES/` links, `NOTES_LIVE`
  inbox, this guide.
- 10/19 — stage folders made physical: `01_CONTENT` / `02_APPROVING` /
  `03_PUBLISHED`; first release backfilled (`2026-10-18_share-seed`).
