# Page Usability Rating Rubric

> Brad directive, 2026-09-17: "lose the business posture — solid by design.
> On every page we rate: ease of use, user-friendliness, ease of
> understanding, navigation, clear-cut direction, information value."
>
> This rubric is the scoring standard. `tools/ux_audit.py` applies the
> automatable parts; judgment dimensions get flagged for eye review.

## Scale

Each dimension scores **1–5**:

| Score | Meaning |
|---|---|
| 5 | A stressed first-time user succeeds with zero help |
| 4 | Works, minor friction |
| 3 | Usable but a real user will stumble somewhere |
| 2 | Confusing, cluttered, or misleading in a way that blocks the task |
| 1 | Broken, hostile, or meaningless to the user |

## Dimensions

### 1. Ease of use — can the user DO the thing?

- Form inputs have visible labels (not placeholder-only).
- Buttons say what they do ("Save journal entry", not "Submit").
- No dead controls, no `href="#"` placeholders, no controls that error.
- Touch targets and tab order make sense.

### 2. User-friendliness — does it feel calm and human?

- Plain language: no legal jargon, no dev-speak, no internal names
  ("FunctionGroupContract", "SSOT", "overlay") in user-facing copy.
- Trauma-informed tone: no urgency tactics, no guilt, no alarm unless the
  user's situation genuinely warrants it.
- No marketing voice: a stressed tenant is not a "lead" to convert.

### 3. Ease of understanding — is it obvious what this page is FOR?

- A heading or first line answers "what is this page" in plain words.
- Content order matches the task order (chronological & spatial rule).
- No unexplained intermediate steps or missing context.

### 4. Navigation — can the user get here, and get out?

- The page is reachable from somewhere a user would actually look.
- A way back/home/forward exists and works (no orphan pages, no 404 links).
- Links say where they go.

### 5. Clear-cut direction — is the next action obvious?

- Exactly one primary action visible, or an obviously ordered set.
- No wall of competing buttons/links with equal visual weight.
- The page ends where the user's job ends — no trailing clutter.

### 6. Information value — does the page deliver something real?

- Real content, not filler, boilerplate, or placeholder text.
- Facts the user can act on — not marketing claims or self-praise.
- Density matches need: no walls of text, no empty pages pretending to be tools.

## Posture flags (automatic deductions / review triggers)

Flagged, not scored — each flag drops the affected dimension by 1 and is
listed in the scorecard:

- **Cost/monetary framing** — banned per `.devin/rules/01-product-positioning.md`.
- **Business posture** — marketing copy, slogans, stat-bars bragging about
  the product, "our platform", sales-style CTAs, corporate voice.
- **Security posturing** — advertising security as a feature ("bank-grade",
  "military-grade", "we take security seriously"). Security is solid by
  design and stated factually (e.g., "documents stay in your storage"),
  never marketed.
- **Account/funnel language** — "sign up", "login", "subscribe", "account"
  in user-facing copy (Semptify has no accounts in the business sense).

## Output

`tools/ux_audit.py` writes:

- `docs/ux/page_ratings_<date>.csv` — one row per page, score per dimension,
  flags, worst-first.
- `docs/ux/page_ratings_<date>.md` — human-readable scorecard for review.

Automated scores are a first pass. Dimensions 2, 3, and 6 always benefit
from an eye pass — the tool marks pages where heuristics are unreliable
(`review: yes`) rather than pretending certainty.
