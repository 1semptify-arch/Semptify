# BILL CAMPAIGN MODULE — reusable procedure spec

*Reference implementation: the Turnbuchalla build (this folder).
Extracted 2026-11-02. This is the meta-document: it documents HOW the
campaign was built so the next bill — or a public Semptify module —
runs the same pipeline without re-inventing it.*

SSOT_LIVE.md covers THIS folder's mechanics. This doc covers the
repeatable system.

---

## What the module does

**Input:** a lived problem with documentation (a case, a pattern, a
system failure).
**Output:** a bill campaign — working statute draft, fiscal model,
champion map, staged outreach, restricted + public share surfaces,
presentation kit, and an accountability ledger showing who stands
for what.

---

## The seven phases

### Phase 0 — Origin (the lived problem)
- The proposal must be anchored in documented harm, not ideology.
  Ours: a $1,348 deposit fight that exposed a system built so the
  weaker party loses by process.
- Freeze the source evidence in `SOURCES/` (links only — masters
  stay frozen).

### Phase 1 — Research pack
Produce six artifacts before anything else moves:
1. **White paper** — the fiscal model + mechanism (ours:
   MODEL_PROGRAM whitepaper — premium math, stress scenarios,
   wins/losses with mitigations)
2. **Accountability levers research** — where the pressure points live
3. **Taxpayer cost research** — the fiscal-note ammunition
   (ours: ~$5,600–$7,400/avoided eviction)
4. **Champion map** — who can carry it (both parties — a bill only
   one side can carry is a bill that dies), opposition forecast,
   continuity picks (pair members who survive election churn)
5. **2-page concept sheet** — the leave-behind
6. **Outreach kit** — per-audience email drafts + skeleton bill

### Phase 2 — The live folder (state machine)
Every bill gets a numbered folder (`NN_The_Bill_<name>`) holding:

| Register | Role |
|---|---|
| `BILL_LIVE.md` | the working statute draft — the only text that matters |
| `DECISIONS.md` | locked design calls — never relitigate, append-only |
| `TASKS.md` | open work, newest first |
| `CONTACTS.md` | every person pitched: role, channel, status, next action |
| `ROADMAP.md` | phase plan — where we are |
| `NOTES_LIVE.md` | visitor feedback from share surfaces |
| `positions.jsonl` | person × provision × stance — silence logged after window |
| `editions.jsonl` | every draft edit: version, date, clause changes, driven-by |

Rule: **registers hold data; docs render from registers.** Anything
that reports state is generated, never hand-maintained (learned the
hard way — the deck went stale against the funding model until it was
regenerated from source).

### Phase 3 — Validation loop
1. **Statute author reads first** — whoever drafted the statute family
   being amended (ours: Birnberg §504B). Their ask is narrow: where
   does this read wrong?
2. **Finance validation** — a housing-finance shop stress-tests the
   model (ours: FHF). Asking for holes, not endorsement.
3. **Hole audit + remediation** — formal pass, fixes applied, dated.
4. **Verification pass** — every public figure checked against the
   claims ledger; unverified figures block publish (or ship marked).

### Phase 4 — Publishing pipeline (two surfaces, two registers)
- **`01_CONTENT → 02_APPROVING → 03_PUBLISHED`** — derivatives flow
  through; masters stay at root.
- **Restricted share** (`share.` domain): invite codes, per-code
  category/level/kind. Bill pack ≠ legal pack — never share them
  under one code. Gates available (disclaimer/conflict/face) —
  currently unused; enabling is a per-share decision.
- **Public page**: publish script converts the live draft → public
  template with three guards — PII strip (private parties never
  appear), claim-check gate (unverified figures blocked or bannered),
  consent register (names only publish with written consent).
- **Git history = the public change log.** The editions register is
  the accountability layer on top.

### Phase 5 — Champion outreach (the send wave)
- Per-audience asks, not one blast: carry (legislators) / validate
  (finance shops) / pilot (agencies) / read-accuracy (drafters).
- **Every send + response lands as a positions row.** Silence after
  the window publishes as "no position recorded" — refusing to engage
  is itself a position.
- **Timing discipline:** never pitch members during an election week.
  Post-certification → pre-filing window is when offices choose their
  agenda. Continuity pairing covers chair turnover.
- **Send gate:** staged bodies live in `02_APPROVING/send-bodies/`.
  Nothing sends itself — a human clicks.

### Phase 6 — Presentation kit
- **Master deck + generator** (`build_presentations.py`): one master,
  per-audience variants inject title "prepared for" + closing ask
  slide. Edit master → rebuild all.
- **Objection card** (from the difficulties doc): if-they-say →
  you-say, per audience.
- **Leave-behind:** the 2-page concept sheet (docx + md).
- Deck must stay synced to the live model — a stale deck that
  contradicts the docs is worse than no deck (caught + fixed 11/02).

### Phase 7 — Two tracks to law
- **Bill track:** member carries → Revisor drafts → committee → floor
  → conference → governor. Pre-filing deadlines land ~Nov–Dec before
  session.
- **Pilot track (no bill needed):** an agency with existing authority
  pilots the model (ours: MHFA on LIHTC properties). Generates the
  local data that becomes the fiscal note. The project can't fully
  fail — if the bill stalls, the pilot still delivered.

---

## Human-in-loop gates (non-negotiable)

| Gate | Rule |
|---|---|
| Sends | staged, never auto-sent |
| Public naming | written consent only (public_consent register) |
| Figures | claims ledger must verify or banner ships "unverified" |
| Strategy | register rows mark owner-decision vs agent-work |

---

## Reusable parts inventory (what ports to a module)

- Folder scaffold: `NN_The_Bill_<name>/` + the register set
- `share_system.py` pattern: codes → category/level/kind/gates
- `publish_bill.py` pattern: live draft → public page w/ PII strip
  + claim gate + consent register
- `build_presentations.py` pattern: master deck → audience variants
- TASKS/ROADMAP/DECISIONS/CONTACTS discipline (the state machine)
- positions/editions ledgers (the accountability layer)
- Email-kit pattern: one audience, one ask, one staged body

## What must be customized per bill

- The statute text + funding mechanism
- Champion map (chamber control changes the map every cycle)
- Fiscal model + taxpayer-cost research
- The evidence spine (aggregate pattern, never PII)

## Anti-patterns — learned, don't repeat

1. **Stale derivatives** — docs teaching an old model (deck vs.
   remediated funding, caught 11/02). Fix: generate from source.
2. **One-audience blasting** — each pitch is a different ask.
3. **Election-week pitching** — dead window; wait for the agenda-
   building window.
4. **Sharing without scope** — level-3 on everything is the default
   trap; bill pack ≠ legal pack ≠ general.
5. **Naming without consent** — public credit requires written OK.
6. **Register vs. campaign register** — victim outreach stays low-key;
   the bill campaign is fully public. Never mix tones.
