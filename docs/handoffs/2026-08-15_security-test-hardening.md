# Handoff: Security Verification + Guardrail Test Coverage + Module Archive

**Standing rules (non-negotiable):**
- One task per commit. Do not combine tasks below into a single commit.
- No self-approval. Flag completion and stop; Brad reviews before merge.
- Preflight read required before touching any file — read the full file, not a diff snippet, before editing.
- If a task reveals scope beyond what's described here (e.g. security headers are missing entirely, not just misconfigured), STOP and report back instead of expanding the fix.

---

## TASK 1 — Verify security headers & rate limiting are actually active

**Why:** `security_headers.py` and `advanced_rate_limiter.py` exist in the repo, but existence isn't evidence they're wired into the running app. Given the prior `PUBLIC_PREFIXES` admin-route exposure, this needs to be confirmed, not assumed.

**Preflight reads (required before any edit):**
- `security_headers.py` — full file
- `advanced_rate_limiter.py` — full file
- The main app factory / entrypoint (wherever middleware is registered — likely `main.py` or `app/core/*`)
- `guardrail_engine.py` — to check whether it already enforces any of this

**Do:**
1. Trace whether `security_headers.py`'s middleware/class is actually registered on the FastAPI app instance (`app.add_middleware(...)` or equivalent). Confirm it runs on every route, not just some.
2. Confirm which headers are actually set: CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, HSTS. List what's present vs. missing.
3. Trace whether `advanced_rate_limiter.py` is applied per-endpoint or globally, and whether it's actually invoked (decorator present on route functions, or middleware registered) — not just defined and unused.
4. Produce a short findings report (markdown, in the PR description — not a new file in the repo) listing:
   - Headers confirmed active
   - Headers missing or misconfigured
   - Rate limiting: active / partially active / defined-but-unused
5. **Do not fix anything in this task.** This is audit-only.

**Acceptance criteria:**
- Findings report exists in the PR description
- No source files modified
- Report explicitly answers: "Is the admin route surface covered by rate limiting?" (given the prior `PUBLIC_PREFIXES` incident)

**Commit message:** `audit: verify security headers and rate limiting are live (no fixes yet)`

---

## TASK 2 — Add tests for guardrail_engine.py and PUBLIC_PREFIXES conformance check

**Why:** Test coverage is ~25%. The guardrail engine and route-exposure conformance check are the highest-consequence code paths given the prior admin-route regression — these should be the first place coverage goes, not general coverage-padding.

**Preflight reads (required before any edit):**
- `guardrail_engine.py` — full file
- Whatever module currently implements or is planned to implement the `PUBLIC_PREFIXES` conformance check (search repo; if it doesn't exist yet as a standalone check, report that back instead of inventing one)
- Existing test directory structure/conventions (so new tests match existing patterns — pytest fixtures, naming, etc.)

**Do:**
1. Write unit tests for `guardrail_engine.py` covering:
   - A route/module that SHOULD pass the guardrail (baseline positive case)
   - A route/module that SHOULD be rejected (e.g. an admin-prefixed route incorrectly marked public) — this is the regression case
   - Edge case: empty/malformed input to the guardrail check
2. Write a test that specifically reproduces the `PUBLIC_PREFIXES` bug class: a route exposure config that *would have* let the prior admin-route regression through, asserting the guardrail now catches it.
3. Do NOT modify `guardrail_engine.py` itself unless a test reveals it currently fails to catch the regression case — if that happens, STOP and report back rather than patching it as part of this task.

**Acceptance criteria:**
- New test file(s) added, following existing test conventions
- All new tests pass against current code
- At least one test explicitly documents (in its name/docstring) that it guards against the `PUBLIC_PREFIXES` admin-exposure regression
- No production code changed unless a failure is found and reported first

**Commit message:** `test: add guardrail_engine coverage incl. PUBLIC_PREFIXES regression guard`

---

## TASK 3 — Archive disabled EXTENDED/RESEARCH tier modules

**Why:** Cheap, low-risk, real startup-time win. Reduces surface area agents have to reason about.

**Preflight reads (required before any edit):**
- `AGENTS.md` — confirm current Tier A/B definitions before touching anything, to make sure "disabled" modules aren't Tier A
- Module registry / manifest (`product_manifest.py`) — to get the authoritative list of disabled EXTENDED/RESEARCH modules rather than guessing from file names

**Do:**
1. Using `product_manifest.py` as source of truth, list every module currently flagged EXTENDED or RESEARCH tier AND currently disabled.
2. Move each to an `archive/` directory (create if it doesn't exist), preserving internal folder structure.
3. Update `product_manifest.py` (or equivalent registry) so archived modules are no longer referenced in active load paths.
4. Do NOT delete anything — this is a move, not a deletion.
5. Confirm app still boots after the move (local smoke test / import check).

**Acceptance criteria:**
- Moved modules boot-tested (app starts without import errors)
- `product_manifest.py` updated to reflect archive locations
- Nothing deleted
- List of archived modules included in PR description for Brad's review

**Commit message:** `chore: archive disabled EXTENDED/RESEARCH tier modules`

---

## Sequencing note
Run Task 1 first — its findings may change urgency/scope for anything else, including whether Task 2's regression test needs to cover more ground than described here. Tasks 2 and 3 can run in parallel across agents since they touch unrelated code paths.
