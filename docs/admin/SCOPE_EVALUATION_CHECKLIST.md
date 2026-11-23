# Scope & Responsibility Evaluation Checklist

> **Status:** Canonical process doc — written 2026-11-14 to document the
> evaluation the retired `BACKLOG.md` assumed existed (it referenced "scope-
> evaluation checklist §3" but the checklist was never committed). First
> applied retroactively in `handoffs/feature-idea-eval-batch-2026-10-24-report.md`;
> the criteria here are that report's substitute criteria, promoted to the
> standing process.
>
> **When this runs:** on every `[considering]` idea before it can be tagged
> `[evaluated]` in the backlog pipeline
> (`[considering]` → `[evaluated]` → `[accepted]` (has ADR) → `[building]`
> → `[done]` / `[watching, not building]` / `[rejected]`).
> Anyone may run it; the runner writes a verdict per idea. Brad resolves
> anything the checklist flags as his call.

Work the sections in order. A fail in §1 ends the eval — don't spend effort
on §2–§5 for something that doesn't belong here.

---

## §1 Scope — does it belong here at all

Canon: `CORE_CONTEXT.md`, ADR-0004 (banned motivations), ADR-0005 (language).

- [ ] **Who does it serve?** If the honest answer is the organization —
      stop. Rejected on arrival; no further evaluation needed.
- [ ] **Time to Real Help.** Does it shorten the path from a person in
      crisis to real help? If it neither shortens the path nor removes a
      real obstacle on it, it doesn't belong.
- [ ] **Never-build list clean.** No accounts, no login, no email capture,
      no engagement/re-engagement mechanics, no tracking, no pop-ups, no
      donation asks on crisis-facing pages, no dark patterns. One hit =
      rejected or redesign until clean.
- [ ] **Pillar fit.** Name the pillar it serves (RECORD / KNOW / ACT /
      GOVERN). If it can't be placed, the idea is probably a bundle —
      split it and evaluate the pieces.
- [ ] **Motivations check.** Not built from fear, resentment, dishonesty,
      or greed — including no urgency tactics and no gap the org wants
      filled for its own sake.

## §2 Responsibility — can we stand behind what it tells a person in crisis

Canon: `docs/admin/PRIVACY_AND_ACCEPTABLE_USE_SSOT.md`,
`app/core/upl_guardrails.py` (UPL tiers), ADR-0009 (fact-check/freshness),
`docs/admin/MOTIVATIONS.md` (Information Integrity Standards).

- [ ] **UPL boundary.** It teaches and routes; it never advises. If the
      feature would say or imply "that's illegal" / "you should withhold" /
      "you have a case" — the answer to that is the attorney's call, and the
      feature must route to legal aid instead. Any output that could read as
      legal advice needs the consequence notice + disclaimer pattern on the
      same screen (see the eviction-defense deadline calculator).
- [ ] **No invented grounding.** Every number, formula, threshold, and
      statute citation must be sourced and verifiable. A fabricated
      formula next to a real citation is the worst outcome this checklist
      exists to prevent — it converts the fact-check system's integrity
      into a delivery vehicle for made-up numbers.
- [ ] **Real-harm failure modes named.** What happens to the tenant if the
      feature is wrong, stale, or half-built? If the harm is financial
      (withhold the wrong amount), legal (miss a deadline), or safety
      (tip off a landlord) — that mode must be designed out or the verdict
      is "viable only after redesign," never "build as-is."
- [ ] **Freshness obligation priced in.** Any data-backed feature inherits
      ADR-0009: source + freshness date on every claim, and an owner for
      keeping it current. If nobody can keep the data fresh, the feature
      isn't ready.
- [ ] **Coverage honesty.** Nominal coverage ≠ verified coverage (e.g.,
      `state-laws.json` marked all 50 states `complete` after a bulk pass
      and still needed a 19-error verbatim fix). Jurisdiction-shaped
      features must say what they actually know and route around gaps —
      never a dead end, never a confident wrong answer.

## §3 Privacy-engineering gate — when standard evaluation is NOT enough

Canon: `docs/admin/PRIVACY_AND_ACCEPTABLE_USE_SSOT.md` (four storage
buckets), `SECURITY_AND_PRIVACY_ARCHITECTURE.md`, ADR-0007,
the 2026-10-27 public-side standard (no user PII ever touches Semptify).

**If any trigger below fires, do not run the standard eval.** The idea
stays `[considering]` and gets a dedicated privacy-engineering review as
its own task, written up as a spec Brad signs off on first.

- [ ] **Cross-tenant aggregation.** Anything deriving signal from more
      than one tenant's records — pattern detection across tenants,
      "tenants like you," shared-building inference. (This is the trigger
      that parked Cross-Tenant Pattern Signal; only a public-records-only
      shape is charter-compatible by default.)
- [ ] **Tenant data moves server-side.** Any field in the `vault_only`
      or `never_collected` buckets that the feature would store, compute
      on, or transmit through Semptify — including "anonymized" versions.
- [ ] **Per-user tracking or analytics.** Activity logs, click/page-view
      history, device fingerprints, behavioral profiles — all on the
      never-collected list.
- [ ] **Consent-gated fields.** Anything outside `server_allowed` for the
      role needs the documented consent gate in §4 of the privacy SSOT —
      if the feature can't articulate the consent story, it goes to review.
- [ ] **Uncertainty defaults to review.** If you can't tell whether a
      trigger fires, it fires. A standard eval must never be the thing
      that decides a privacy question — that needs the dedicated review.

## §4 Feasibility & fit — what would building it actually take

- [ ] **Overlap check against live code, not docs.** Find the modules that
      already do adjacent work and read them — a recorder vs. a lookup
      facade vs. a storage mapping are different things even when names
      sound the same. Duplicate → `[watching, not building]` or merge;
      complementary → name the integration points.
- [ ] **Existing assets.** Mockups, built-but-unwired machinery, law
      content, proven page patterns — reuse beats new build. Thin facades
      over existing systems are the high-leverage shape.
- [ ] **Data feasibility.** Can the content actually be sourced, per
      county/state where applicable, and kept fresh? Scrape-fleets and
      data we can't maintain are feasibility failures, not stretch goals.
- [ ] **Build cost vs leverage.** Small surface, big crisis-shaped win is
      the preferred shape. A large build for a narrow case needs to
      justify itself against Time to Real Help directly.

## §5 Verdict & hand-off — what the eval produces

For each idea, the eval writes a short record:

1. **Verdict** — one of: `build` · `build with conditions` (conditions
   named) · `parked — needs <specific review>` · `rejected — <reason>`.
2. **What exists** — modules/content/mockups verified in the repo.
3. **Pillar** — the assigned pillar, or why it was split.
4. **Top risk** — the one failure mode a reviewer must not miss.
5. **Recommendation** — one sentence on what happens next.

Then update the tag: passing ideas move `[considering]` → `[evaluated]`;
parked ideas stay `[considering]` with a note naming the review they need;
rejects get `[rejected]` with the reason so the idea isn't re-litigated
from memory later.

**Escalate to Brad instead of guessing when:** a §3 trigger fired; the
verdict needs a legal judgment call; the build would spend real money or
need a partnership Semptify doesn't have; or two acceptable designs split
on a question of taste.

---

*Related: `archive/consolidated-2026-10-24/BACKLOG.md` (the tag pipeline
this gate sits in), `docs/admin/SEMPTIFY_BUILD_CONTRACT.md` (what ships
after `[accepted]`), `docs/admin/PRIVACY_AND_ACCEPTABLE_USE_SSOT.md`
(the §3 enforcement layer).*
