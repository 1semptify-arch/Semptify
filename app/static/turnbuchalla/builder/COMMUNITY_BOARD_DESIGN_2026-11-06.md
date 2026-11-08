# COMMUNITY BOARD — design for the public discussion layer

*Dated design doc — frozen once written, per folder convention. Status:
DESIGN ONLY — nothing here is built. Flagged by Brad 10/31; specced
2026-11-06 (swe-2, queue task
plan-20261031-community-board-public-discussion-layer--8512).*

---

## What this is

A public discussion layer for the share/bill platform — the place where
readers stop talking *to* the drafting table (one-way, today's Inkwell)
and start talking *on the record, to each other, about the draft*.

The platform's own metaphor already dictates the shape. Marks are
"numbered, dated, and attached to a clause." They "appear in the public
record once read into the ledger." The record "does not erase, it amends
in the open." That is not a forum — that is a **public comment docket**,
the same shape as a legislative comment period or regulations.gov. This
design extends that metaphor rather than bolting a chat/forum onto it.

**The one-line version:** every mark stays a mark — but once read in, it
gets a public number, sits on the record next to its clause, and later
marks can answer it *by reference*. Discussion is what the ledger looks
like over time.

## What exists today (verified against live files 2026-11-06)

| Piece | State |
|-------|-------|
| `index.html` per-clause `+` annot links → `comment.html?c=<clause>` | Built, works |
| `comment.html` — the Inkwell (clause, mark, optional name, optional email) | Built; **submit is a mailto stub** — "comments register endpoint" not wired |
| `supporters.html` — the roll (name, town, optional line) | Built; **also a mailto stub** |
| `record.html` — editions ledger + positions table | Built; render targets `editions.jsonl` / `positions.jsonl` named in HTML comments, **no renderer exists** |
| Share side — `share.semptify.org/bill/?code=` gated links, `:8899` codes, visitor notes → `bill_notes.jsonl` | Live per TASKS.md 10/18. Ops code (`ops_console.py`) lives case-side, outside this repo — **not re-verified this pass** |
| Public delivery — static pages via `bill-mirror` Cloudflare worker (GitHub repo `semptify-bill-mirror`), plus the in-repo copy under `app/static/turnbuchalla/` | Live; Render origin down (Neon quota) — mirror is the live path |

**Consequence:** the intake side is *promised* (the page copy already
tells readers their mark enters the record) but only delivered by mailto
to brad@semptify.org. Every mark today lands in Brad's inbox, not a
register. The board design below assumes Phase 0 — real intake — ships
first; it is needed regardless of whether the board ever opens.

## How others have solved this (research pass)

| Model | Who uses it | What fits us | What doesn't |
|-------|-------------|--------------|--------------|
| **Public comment docket** (regulations.gov, MN public-comment periods) | Rulemaking, committee testimony | Everything — numbered comments, public posting, responses by reference, no accounts, human screening is expected | None — this is the load-bearing precedent |
| **Margin annotation** (hypothes.is, Madison/OpenGov clause comments) | Document-drafting collaboration | Clause anchoring — we already have it via `?c=` | Their live-threaded reply UI assumes accounts + real-time |
| **Hearing record / town hall** | Legislative process | "Drafter answers in the open" — Q&A becomes part of the record | None — cheap and fits |
| **Discourse/forum** (threaded board) | Communities | Real discussion feel | Accounts, presence mechanics, heavy moderation, engagement metrics — banned by Semptify core rules |
| **Giscus/Disqus** (embedded comment engines) | Blogs | Zero build | Trackers, third-party accounts required, data leaves our control — rejected |

**Verdict:** the docket model. Serialized, numbered, moderated by
read-in, response-by-reference. It is the only option that satisfies all
four constraints simultaneously: the platform metaphor, the Semptify
no-accounts rule, zero-cost operation, and the campaign's transparency
claim (a hostile reader can audit the *process*, not just the text).

## The design

### Surface names (recommendation — Brad decides)

- **The Margin** — the per-clause public layer: read-in marks shown
  attached to their clause. (Extends the existing "marginalia, made
  public" language on comment.html.)
- **The Floor** — the open layer for questions not tied to a clause
  (Phase 2). Drafter answers get entered into the record the same as
  everything else.

Alternative single-surface option: extend `record.html` with a third
ledger — "Marks read in" — and skip new page names entirely. Cheaper,
slightly less discoverable.

### Data model

Two files, mirroring the queue→ledger split that already exists:

- `marks_intake.jsonl` (private, ops-side) — everything submitted.
  Never published raw.
- `marks_public.json` (or `.jsonl`) — only read-in marks, rendered into
  the static tree at publish time. This is what pages fetch.

Mark record:

```
id           M-0001 (sequential, issued at read-in — intake keeps its own key)
clause       "I-3" | "References" | null (general)
body         text, plain language, no markup
name         string | null  (null renders "unsigned")
reply_to     "M-0037" | null
submitted_at ISO ts
read_in_at   ISO ts | null
status       queued | read_in | held | crisis_routed
source       "site" | "share:<code-owner>" | "mail"
email        intake-only field — NEVER rendered, never copied to public file
```

`reply_to` is a citation, not a thread. Responses render in-line in
chronological order with a "re: M-0037" tag — the record stays linear.

### Flow

```
reader → Inkwell form (or mail, or share-link note)
       → POST to ops endpoint → marks_intake.jsonl   [replaces mailto]
       → human read-in (triage: publish / hold / crisis-route)
       → read-in marks appended to marks_public.json
       → static pages render them (record.html ledger + per-clause margin)
```

The human read-in is not a moderation bolt-on — it is the promise the
site already makes ("will appear in the public record once read into the
ledger") and the only moderation layer this design needs.

### What renders where

- **`record.html`** — new third ledger, "Marks read in": table of
  number / date / clause / mark / name. Deep-link anchors `#M-0001`.
- **`index.html`** — the `+` annot link gains a count badge
  (`+ 3` = three marks read in on that clause) once marks exist;
  no badge while empty — silence is honest, not broken. Requires
  `build_platform.py` to emit the badge slot (small change: annot link
  gets a `<span class="annot-count">`; counts injected at publish, not
  page-load JS, so the file stays fully static).
- **`comment.html`** — unchanged except `?re=M-0042` param prefills a
  "Re: mark M-0042" line above the form, and the submit goes to the real
  endpoint instead of mailto.
- **Share side** — gated `?code=` visitor notes already save to
  `bill_notes.jsonl`; fold them into the same intake with
  `source: share:<code-owner>` so a champion's guests' marks are
  attributable to the invitation, not the public web.

### Response mechanics

- Any rendered mark carries a "mark this" affordance →
  `comment.html?re=M-XXXX` → response enters the same intake with
  `reply_to` set.
- No nesting UI. A response is a new mark that cites the old one.
  Threads emerge as chains of citations in the ledger — browsable,
  auditable, impossible to brigade a sub-thread.
- One level of indirection max at render: a mark shows "re: M-XXXX" and
  that's it. No quoted blocks — quoting invites reply-frag wars.

### Intake endpoint (Phase 0 prerequisite)

- `POST /marks` on the existing ops stack (`:8899`, behind the
  `share.semptify.org` tunnel) → append `marks_intake.jsonl`. Same
  pattern as `bill_notes.jsonl` — zero new infra, zero cost, local-only.
- For the unauthenticated public path: Cloudflare Turnstile (free) or a
  simple honeypot field + per-IP rate note in the intake record. No
  accounts, no email verification — a name is optional and unverified by
  design (the record says "signed," not "verified").
- Read-in = small ops_console addition or a script: list queued marks,
  Brad marks each `read_in`/`held`/`crisis_routed`, regenerate
  `marks_public.json`, copy to `SHARE/` + mirror repo in the same
  publish stroke that SSOT_LIVE already mandates.

### Crisis routing (non-negotiable, per Semptify core rules)

A mark from someone describing their own live eviction is not a comment
— it's a person in crisis hitting the wrong door. Rules:

1. The form shows one line above the box: *"If this is about your own
   housing right now — help lines first: [HOME Line 612-728-5767].
   This page is for the draft."*
2. Triage option `crisis_routed`: mark is held from the public record,
   counted as received, and the read-in tool drafts a reply (email if
   given, else nothing — no account means no push) pointing at help
   resources. Never a dead end.
3. Marks_public.json never carries crisis content.

### PII and legal guards

- Email never rendered, never leaves intake file.
- Guidance line on the form: "No addresses, no case numbers — the
  record is public and permanent."
- UPL guard: the Margin is for the draft, not legal advice; the existing
  "nothing here is filed law" footer already covers the frame. Marks
  asking case-specific legal questions get the crisis-routing lane
  (above), not a public answer.
- Read-in redaction right: Brad may trim a mark's PII on read-in; the
  redaction itself is entered in the record (`[redacted: address]`).

### Fairness axiom applied

Landlord, industry, and opposition marks read in on the same footing —
numbered, dated, answered in the open. The campaign's bipartisan frame
(consumer protection left / court-cost savings right) only survives if
hostile marks are *visible and answered*, not filtered. Held = spam,
abuse, PII violations, off-topic — never held for disagreeing.

## SWOT

**Strengths**
- Extends machinery that already exists (annot links, intake stub, ledger
  pages, ops notes) — small delta, no new platform.
- Zero cost: static publish + existing local ops stack; no third-party
  service, no accounts, no database.
- The human read-in doubles as moderation, legal review, and the
  campaign's transparency proof — three functions, one step.
- Serialized citation discussion can't develop pile-on dynamics; there
  is nothing to dogpile *on* — no live thread.

**Weaknesses**
- Read-in latency: a mark can sit queued until Brad processes it. Not a
  live conversation — sets the wrong expectation if labeled "board."
- Single-moderator bottleneck and single point of failure (Brad's time).
- Static render means page content only refreshes at publish strokes.

**Opportunities**
- Opposition marks answered in the open become campaign assets — "they
  attacked clause II-3, here's the answer, it's in the record."
- The marks ledger is itself evidence for committee staff: real public
  engagement, documented, dated.
- `?re=` citation chains surface which clauses draw fire — a free
  heat-map of the bill's contested points.

**Threats**
- Astroturf: coordinated landlord-industry marks. Mitigated by read-in
  (nothing publishes unscreened) but a flood still costs Brad triage
  time — watch volume, consider per-source batching.
- A crisis post missed in triage = a person in danger left hanging.
  The `crisis_routed` path must exist before Phase 1 ships.
- PII posted publicly before read-in is caught — mitigated because
  nothing publishes pre-read-in *by construction* (public file only
  contains read-in marks).

## Gaps (honest)

1. **Intake doesn't exist yet.** Both forms are mailto stubs. Phase 0
   is load-bearing and not built.
2. **No renderer for any `.jsonl`** — `record.html` names
   `editions.jsonl`/`positions.jsonl` in comments; nothing renders them.
   The marks renderer would be the first real one — build the pattern
   once and it serves all four ledgers.
3. **Ops-side code not verified this pass** — `ops_console.py`,
   `bill_notes.jsonl` handling, and `:8899` routes live outside this
   repo (case-side stack). The Phase-0 endpoint spec above assumes the
   TASKS.md description is current.
4. **Publish path to the mirror** — how `SHARE/` and
   `semptify-bill-mirror` get updated today isn't documented in-repo;
   `marks_public.json` must ride whatever that stroke is.
5. **Read-in tooling** — Brad triaging raw JSONL by hand won't scale;
   needs a small console surface (list/check/route) before Phase 1.

## Recommended phasing

- **Phase 0 — wire the intake (prerequisite, do regardless):**
  `POST /marks` → `marks_intake.jsonl`; retire both mailto stubs; roll
  signatures → `supporters.jsonl` the same way. Small, testable,
  unblocks everything including today's promised behavior.
- **Phase 1 — The Margin:** marks renderer (`marks_public.json` →
  record.html third ledger + per-clause anchors), `?re=` citation
  responses, `+ N` count badges via `build_platform.py`, read-in
  tooling, crisis-routing lane. Ship when intake has run clean for a
  couple of weeks — or earlier if Birnberg/FHF rounds generate marks
  that deserve public answers.
- **Phase 2 — The Floor (decide after Phase 1 volume):** open questions
  not tied to clauses, drafter answers entered into the record like
  hearing testimony. Only if Phase 1 shows demand for cross-clause
  discussion.
- **Never:** live threading, votes/reactions, notifications, profiles,
  presence of any kind — engagement mechanics, banned by core rules and
  they'd poison the ledger metaphor.

## Decisions for Brad (open — not decided here)

1. Surface name: "The Margin" + "The Floor" vs. one extended "Record"
   ledger.
2. Read-in cadence commitment the site can honestly promise (the current
   copy says "once read into the ledger" — no clock promised; keep it
   that way or state a window).
3. Do signed and unsigned marks render identically except for the name
   field? (Current copy implies signed marks carry more public weight.)
4. Share-side gated notes (`bill_notes.jsonl`) and public marks: one
   register or two? (Recommendation: one intake, `source` field
   distinguishes.)
5. Citation-only responses — confirm no threading UI ever, or revisit
   at Phase 2.
6. Crisis-routing help-line copy — which resource list is canonical for
   this surface (HOME Line used above; confirm vs. semptify.org's
   standard block).
7. Turnstile vs. honeypot+rate-limit for the public POST (cost: both
   free; Turnstile = one more third-party call in the page).
