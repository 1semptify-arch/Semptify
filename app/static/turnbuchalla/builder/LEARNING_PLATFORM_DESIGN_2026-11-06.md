# LEARNING PLATFORM — design for the public education layer

*Dated design doc — frozen once written, per folder convention. Status:
DESIGN ONLY — nothing here is built. Flagged by Brad 10/31; specced
2026-11-06 (swe-2, queue task
plan-20261031-learning-platform-educational-layer-alon-1e23).*

---

## What this is

The public education layer on semptify.org — the third surface in the
same family as the bill (`/bill`) and the community board (Margin/Floor,
designed 2026-11-06). Where the bill is *advocacy* and the board is
*discussion*, this is *teaching*: the KNOW pillar's public face.

MOTIVATIONS.md §4 already names this the next frontier — "the
Information layer... Semptify should be elite-class among housing
information advocacy platforms." The pieces exist scattered (a law
library, an articles pipeline, three standalone guides, state-law data).
Nothing organizes them into something a stressed person can *walk
through*. That is the gap this layer fills.

**The one-line version:** a shelf of guided reading paths — each course
a short, ordered sequence of plain-language lessons drawn from canon we
already own, rendered from a register and published static like the rest
of the family. No accounts, no enrollment, no scores. The reader's
progress lives in the URL and a printed checklist, never on our servers.

## What exists today (verified against live files 2026-11-06)

| Piece | State |
|-------|-------|
| `/law-library` page + `/api/law-library` | Live and public — path exempted in `storage_middleware.py` ("public education content"), page served from `app/main.py` (`pages/law_library.html`, statute/reference browser). `LAST_VERIFIED_DATE = "2025-01-01"` is hardcoded in the router — the freshness badge it renders is stale by ~10 months. |
| `app/data/articles/<subject>/` pipeline | 18 subject dirs staged via `content_request.json`; only `credit` and `retaliation` have fulfilled `articles.json`. **Nothing in `app/` renders `app/data/articles/` yet** (verified — zero code references; content is pipeline-staged only). |
| Standalone public guides | `/credit-reports`, `/document-everything`, `/complaints` shipped via `PortalPage` registry + `public_shell.html` — the proven "one authored guide" pattern, additive per page. |
| `static/data/state-laws.json` | **Drifted since the audit** — the 2026 Know-Your-Rights audit said 12/50 states complete, 38 stubs. The current file marks 44 `status: "complete"` + 6 `partial`, and depth varies wildly: MN carries 3 `housing_laws` entries; the 6 `partial` states (WI, MO, IA, ND, SD, IN) carry none. No `last_updated` at file level. Treat per-field currency as unverified. |
| `context_explanation_entries` | ADR-0008 Layer-1 pool: 56-row workbook with placeholder prompts, 3 example entries loaded. `review_status: beta | vetted` gate exists and is the correct reuse point for lesson content status. |
| "Semptify Live" | Issue Nº 001 already exists — `/what-the-bill-changes` ("Cover story — Issue Nº 001"). An editorial surface is born but has no second issue. |
| Bill surface | `/bill`, `/bill/live`, `/bill/research`, `/your-voice` live on the app + static mirror via `bill-mirror` worker (GitHub `semptify-bill-mirror`). Per last state docs the Render origin was down (Neon quota + cold-boot); **the mirror is the reliable public path — verify at build time.** |
| Community board | Designed, unbuilt — `COMMUNITY_BOARD_DESIGN_2026-11-06.md`, same folder. |

**Consequence:** the *material* for education exists but has no
curriculum shape — a renter lands on a library or a one-off guide and is
left to self-sequence while stressed. And the one surface that could
carry lessons reliably today is the static mirror, not the app.

## How others have solved this (research pass)

| Model | Who uses it | What fits us | What doesn't |
|-------|-------------|--------------|--------------|
| **Legal-aid library** (LawHelpMN, LawHelp.org) | State legal aid | Plain-language topical articles, visible sourcing, no interactivity | Article-pile: no guided order, reader self-sequences under stress — the exact gap |
| **Authored handbook** (HOME Line's tenant book) | MN tenant hotline | One authored voice covering the whole arc — proven it works in MN | It's a book: long, linear, no entry points, heavy to maintain |
| **Microlearning** (Khan-style short lessons + self-checks) | Online education | Short units, sequenced paths, "check yourself" moments | Accounts/enrollment/progress-tracking are load-bearing in their model — banned here; we keep the shape and drop the tracking |
| **Learning-in-doing** (JustFix.nyc) | Nonprofit tenant tools | Every lesson ends in a *do*: check your lease, pull your report, log the notice | Tool-first, not course-first — it's a layer inside, not the frame |
| **Court self-help centers** (mncourts.gov) | Judiciary | Chronological task order — matches our standing GUI ordering rule | Institutional tone, jurisdiction-locked, assumes you already know your problem's legal name |
| **LMS** (Moodle etc.) | Schools | Structured curriculum | Accounts, enrollment, completion tracking, quizzes that submit — rejected wholesale by core rules |

**Verdict:** guided reading paths over a canon pool. A *course* is a
syllabus register — an ordered list of lessons, nothing more. A *lesson*
is a short authored page that teaches one thing and points deeper into
canon. The shape of Khan (short, sequenced, self-checking), the
governance of the docket family (registers, human gate, static publish),
the privacy of the record (nothing about the reader leaves the device).

## The design

### Surface names (recommendation — Brad decides)

- **The Reading Room** — keeps the building metaphor (lobby, concierge,
  upper floors; this folder is already "the builder's room"). Courses
  sit on the shelf; a course is a reading path.
- **The Primer** — name the surface after its flagship content if only
  one course ever ships.
- **Plain "Learn"** (`/learn`) — honest and SEO-legible, least in-family.

Cheapest alternative, no new name: fold reading paths into the existing
`/law-library` page as a paths index. Not recommended as primary —
`/law-library` is app-rendered, and the app is the fragile path right
now; the mirror is live.

### Data model — registers, not pages

Two authored registers + one generated index, same discipline as
positions/editions/marks in the family:

- `curriculum.json` — courses: `id`, `title`, `promise` (one plain
  line), `audience_note`, ordered `lesson_ids`, `status`
  (`draft | published`).
- `lessons.json` — lessons: `id`, `course`, `seq`, `title`,
  `body_md` (short — see standard below), `canon[]` pointers
  (`{type: article | statute | guide | state_law | bill_clause |
  live_issue, ref}`), `sources[]`, `jurisdiction` (`MN | varies |
  general`), `upl_tier`, `review_status` (`beta | vetted` — same gate
  as the articles pipeline), `last_reviewed`.
- `canon_index.json` — **generated, never hand-maintained**: every
  citable piece in the pool (articles.json entries, law-library
  statutes, state-laws fields, PortalPage guides, bill clauses) with a
  stable ref. Registers hold data; docs render from registers — the
  family's own stale-derivative lesson applies here verbatim.

### Flow

```
authored lessons.json + curriculum.json + canon_index.json
       → build_learning.py (pattern of build_platform.py)
       → static lesson + index pages into the publish tree
       → same stroke as SHARE/ + semptify-bill-mirror
```

Optional second render target once the Render origin is healthy: a
`PortalPage` entry + `public_shell` Jinja reading the *same* registers —
one register, two renderers, mirror stays primary while the origin is
fragile.

### What renders where

- **Shelf index** — courses listed with one-line promises. No
  marketing, no "featured," no counts that would shame an empty shelf —
  silence while a course is draft is honest, matching the `+ N` badge
  rule on the bill.
- **Course page** — the syllabus: ordered lessons, "step N of M,"
  a printable checklist affordance (progress the reader can hold).
- **Lesson page** — the standard unit:
  - ≤ ~350 words of body, plain language (the 10-seconds-on-a-cracked-
    phone bar from CORE_CONTEXT).
  - One thing taught, in chronological/spatial order (first thing first).
  - "Where this comes from" — visible sources, per Information
    Integrity §7.
  - "Go deeper" — the `canon[]` links into law library / articles /
    state law / bill clauses.
  - One next-step link at the bottom — the next lesson, or "back to
    the shelf." Never a menu of decisions.
  - `last_reviewed` rendered; beta-status content carries the lighter
    disclosure; unverifiable claims don't ship (ADR-0009 rule).
- **Cross-links, offered not pushed** — bill pages may offer "new to how
  deposits work? → the primer"; lessons may link a bill clause as "one
  answer being tried in Minnesota, still a draft." Both directions are
  labeled and honest — Attraction Principle: we offer, the reader chooses.

### Reader-held progress

No accounts means the record of "how far did I get" belongs to the
reader, not to us: `step N of M` on every lesson page, stable URLs a
reader can bookmark, and the printable checklist. Optional later: a
session-local "where was I" note — nothing stored server-side ever, by
construction, not policy (the Experience Token's own privacy model,
applied to a surface that needs even less of it).

### Self-checks (open decision)

Possible without any tracking: client-side disclosure widgets —
"Think you know? → reveal." No submission, no scoring, nothing leaves
the device. If Brad wants them, they ship inside lesson pages; the
default design needs none.

### Crisis routing (non-negotiable, same lane as the board)

Any lesson touching eviction, notices, or deadlines opens with the
one-line pointer — *"If this is about your home right now: help lines
first — /help."* Lessons teach the map, never the move: "what do I do
about MY case" is the help lane or a real attorney, not a lesson. The
canonical help copy comes from `/help` — one source, no forked wording.

### Integrity and language guards (inherited, mechanical)

- Sources on every lesson — no sourced claim, no ship.
- `review_status` gate: beta lessons render with the lighter disclosure;
  vetted renders as settled. Same semantics as articles.json.
- Banned-language scan on build: no "evidence"/"proof" pre-court, no
  adversarial words, no "free" describing Semptify, no business terms,
  no urgency tactics.
- AI-disclosure footer where lessons are AI-drafted.
- Jurisdiction label explicit per lesson — default is `general` or `MN`;
  nothing pretends national coverage while state-laws depth is
  unverified.
- Numeric/public claims ride ADR-0009 freshness (ContextFact +
  scheduled verification), never hardcoded.

### What a lesson is NOT

Not an article dump (it's short). Not advice (map, not move). Not a
course in the enrollment sense. Not generated live — everything is
authored and reviewed before publish, the same human gate as read-in on
the board and the claims ledger on the bill.

## SWOT

**Strengths**
- Reuses the canon pool, the articles pipeline, the publish stroke, and
  the review_status/freshness gates — small delta, no new platform.
- Zero cost: registers + static publish; no service, no accounts, no DB.
- Education is the stated next frontier — this gives §4 a shape that
  fits every standing rule instead of fighting them.
- The mirror-first render means the layer survives the Render origin
  being down — arguably the only public surface family that's resilient
  today.

**Weaknesses**
- Content depth is the real bottleneck: 2/18 article subjects fulfilled,
  state-laws thin, law-library badge stale — a curriculum exposes the
  thinness rather than hiding it.
- Single author/editor bottleneck (Brad) again — same as read-in on the
  board.
- Static render means pages refresh only at publish strokes.

**Opportunities**
- The bill hands the first course its subject and its audience —
  deposits/rent assurance taught plainly makes the bill legible to
  non-lawyers, and the lessons make Semptify legible as "the place that
  teaches."
- Lessons are citable units — advocates and caseworkers can send one
  link ("read lesson 3") instead of a library.
- The primer is reusable across bills — the next campaign inherits the
  shelf.

**Threats**
- Stale legal info is real harm — law drifts and the state-laws file has
  already drifted once. Mitigation: `last_reviewed` rendered, freshness
  wiring on claims, jurisdiction labels, beta disclosure.
- UPL drift if lessons slide toward case-specific answers — the
  map-not-move rule and crisis lane are the guardrails.
- Scope creep toward LMS features (progress bars, badges, accounts) —
  every one of those is a banned-motivation violation in disguise.

## Gaps (honest)

1. **The pool is thin** — 2/18 article subjects fulfilled; the
   curriculum depends on the pipeline producing. Sequencing Phase 1 on
   the bill's home ground (deposits) is partly *because* that canon is
   freshest.
2. **No renderer exists for any register in the family yet** — the
   lesson renderer shares the gap with the marks renderer (community
   board gap #2). Whichever builds first sets the pattern; build it once.
3. **state-laws.json depth unverified** — the file restructured since
   the audit; lessons must not cite it as authoritative until a
   freshness pass lands. Flagged, not fixed here.
4. **Law library staleness** — `LAST_VERIFIED_DATE` hardcoded
   2025-01-01; lessons citing statutes need a verification lane
   (revisor.mn.gov check at build time is the natural shape).
5. **Publish mechanics live outside this repo** — the SHARE/mirror
   stroke details are case-side (same as community gap #4).
6. **Render origin health** — last state docs have it down; the
   Jinja second-render path waits on it. Verify at build time.

## Recommended phasing

- **Phase 0 — the registers + canon_index generator (prerequisite, do
  regardless):** schema the two registers, generate the canon pool
  index, publish nothing. Small, testable, unblocks everything.
- **Phase 1 — The Primer + lesson renderer:** one course (~8–12 short
  lessons) on the bill's home ground — what a deposit is, what a notice
  means, what a dated record buys you — ending where the bill picks up.
  Static publish via the mirror stroke; shelf index page.
- **Phase 2 — subject paths:** sequence the remaining subjects as their
  articles fulfill; state-law lessons gated on the freshness pass;
  `/learn` (or chosen name) `PortalPage` entry once the origin is
  healthy.
- **Phase 3 — depth without tracking:** client-side self-checks,
  canon cross-refs, optional session-local "where was I," Semptify Live
  issue companions to evergreen lessons.
- **Never:** accounts, enrollment, certificates, scores that leave the
  device, quizzes that submit, progress dashboards, engagement
  mechanics of any kind, live AI-generated answers.

## Decisions for Brad (open — not decided here)

1. Surface name: "The Reading Room" / "The Primer" / plain `/learn` —
   or fold into `/law-library` as reading paths (not recommended while
   the app is the fragile path).
2. Render target: register → static mirror first (recommended while the
   origin is down), Jinja second — or Jinja-first.
3. First course: deposits/rent-assurance primer (bill-adjacent, canon
   freshest) vs a broader "housing 101."
4. Self-checks: client-side disclosure widgets — ship with lessons or
   skip.
5. Lesson standard: ~350-word body + visible sources + one deeper link
   + one next step — confirm, or adjust the bar.
6. "Semptify Live" relationship: sibling surfaces (Live = timely/
   editorial, Learning = evergreen/sequenced, cross-linked) — or one
   layer.
7. Authorship lane: lessons ride the content_request/articles.json
   pipeline (recommended — one lane, one review_status semantics) or a
   parallel lesson-request register.
8. Crisis/help copy: reuse `/help`'s canonical block verbatim
   (recommended) — or a lesson-specific variant.
