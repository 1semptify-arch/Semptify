---
mode: agent
description: Mandatory pre-flight check - run this before starting any work session
---

# Preflight Prompt

<!-- Mirrors .devin/skills/preflight/SKILL.md — keep both in sync when editing. -->

## Semptify Pre-Flight Check

Run this at the start of EVERY session. No exceptions.

### Step 0: Semptify is NOT a business model — Read this first

Semptify is a **public utility, not a product.** Read `CORE_CONTEXT.md` in the repo root before writing or approving any copy, UI text, or feature. Enforce these rules:

- **North star metric: Time to Real Help.** Not sessions. Not return visits. Not engagement. Not signups. Every feature either reduces Time to Real Help or it doesn't belong.
- **NEVER use the word "free"** on any page, button, label, or description — *when describing Semptify itself*. Saying "free" insinuates we charge for other things. We don't. We never have. We never will. **Exception:** factual descriptions of external resources (e.g., "Free legal help for low-income tenants" describing Legal Aid) are permitted — these are facts about *their* services, not Semptify self-promotion.
- **NEVER use business-model terminology** — no "accounts", "log in", "sign up", "subscription", "upgrade", "premium", "paid plan", "trial", "pricing", or similar. These words imply a commercial product. Semptify is not one.
- **No advertising — ever.** No banner ads, no sponsored content, no affiliate links, no tracking pixels for ad networks. This is non-negotiable and permanent.
- **Listing vs advertising — there is a difference.** A *listing* is a neutral directory entry of a resource (e.g., "HOME Line MN — 612-728-5767"). An *advertisement* is promotional content paid for or placed to generate revenue/clicks for the advertiser's benefit. Listings are permitted only when:
  - The resource is directly relevant to tenant housing rights
  - The user (project owner) has reviewed and approved the specific listing
  - The listing is neutral, factual, and non-promotional
  - **When in doubt, do NOT add the listing. Ask the user first.**
- **There must never be a dead end.** Every error page, every broken flow, every moment of confusion must route the user toward real help. Not leave them hanging.
- **If you see existing text that violates these rules**, flag it to the user and propose a fix. Do not silently leave it.
Semptify is a nonprofit tenant-crisis tool, not a product. No accounts,
no login, no email capture, no analytics, no popups, no engagement
features. If a feature serves the org and not a user in crisis, do not
build it — flag it and stop instead.

Do not add new features.
Do not create new markdown files. If you think something else is broken,
list it at the end of your response under "Noticed but not fixed" —
do not touch it — and log each item to the master-repo intake queue so it
isn't lost between sessions:

```powershell
python C:\master-repo\tools\orchestrator_intake.py log `
  --found "<what you found>" `
  --location "<file/module or window>" `
  --why "<why it's out of scope for this task>" `
  --severity low|medium|high --source <agent-id>
```

The orchestrator triages intake into real tasks or dismisses with a reason.

### Step 1: Prove you know Semptify — NO LAZY WORK

**Before you touch a single file, you must demonstrate working knowledge of this system.** If you cannot answer these from the docs, you are not ready to write code. Go back and read until you can.

`REQUIRED_READING.md` is the canonical manifest for what to read — Tiers 1+2 are mandatory here. In order:

1. `AGENTS.md` — Full document including Known Failure Registry (all items)
2. `ACTIVE_CONTEXT.md` — Current priority; do not start something else
3. `BUILD_STATE.md` (last 2 entries) — What shipped, what is broken, what is pending
4. `PROJECT_BIBLE.md` — Governance, gate chain, onboarding flow, doc hierarchy
5. `CORE_CONTEXT.md` — What Semptify IS, who it's for, what we never build
6. `docs/admin/MOTIVATIONS.md` — Foundational motivations, language rules, Information Integrity Standards
7. `docs/AI_TEAM_OPERATING_PROTOCOL.md` — Collaboration protocol and decision authority
8. `docs/adr/` — all ADRs (currently 0001–0009): permanent decisions, never edited
9. `SEMPTIFY_SYSTEM_MANIFEST.md` — Module registry; required before touching modules/routers

Then **state the following out loud** before proceeding (this is your proof of comprehension):

- What Semptify is (one sentence — if you say "product" or "SaaS" you failed)
- The Four Pillars (RECORD, KNOW, ACT, GOVERN) and what each one does
- The gate chain for onboarding (what gates exist, what order)
- The Python version mandate and why it exists
- At least 3 items from the Known Failure Registry that are relevant to your task
- What SSOT means in this codebase and why hardcoded URLs are banned
- What the Forge is and how module lifecycle works

#### If you cannot state these clearly, STOP. Do not proceed. Do not guess. Do not wing it

We do it right or we don't do it at all. There is no "figure it out as I go" here. Every lazy shortcut costs hours to fix. The history in AGENTS.md proves this. Read it. Learn it. Then work.

### Step 1a: Freshness & canonicity check — NO SHALLOW SIGNALS

**Finding a file that looks related is not the same as having current, complete context.** This repo has multiple parallel/legacy systems for the same concern, and `gap_report.py` / `GAPS.md` are known to lag behind actual repo state. A filename match, a single grep hit, a keyword search, or a doc's claim of "resolved" is a lead to verify, never a fact to act on.

Before you rely on any file, doc claim, or search hit to justify what you're about to do:

1. **Read the full file(s), not a snippet.** A grep hit or search-tool excerpt tells you a string exists somewhere — it does not tell you the surrounding logic, whether the code path is even reachable, or whether it was superseded last week. Open and read the whole file before treating it as ground truth.
2. **Cross-check against the live repo state, not just the doc that describes it.** `BUILD_STATE.md`, `ACTIVE_CONTEXT.md`, `GAPS.md`, and `tools/gap_report.py` output all drift from reality — they are inputs to verify, not verified facts. Confirm the function/route/table/flag you're relying on actually exists and behaves as described by reading the current code, running it, or checking the schema — not by re-reading the doc that claims it.
3. **If your task touches one of the known-duplicated/legacy areas below, identify which copy is canonical before doing anything else.** Do not read from, extend, or "fix" whichever copy you happened to find first.

   | Area | Status (verify before trusting) |
   |---|---|
   | **Design tokens / palettes** | `template-N` classes (5 role palettes defined in `static/css/ssot-design-system.css`) are canonical per `docs/admin/DESIGN_TOKEN_WORKBOOK.md` §10.1 (decided 2026-09-14). `static/css/themes/` (5-theme crimson/forest/ocean/royal/slate switcher) is legacy and unrelated to template-N — retirement undecided (§10.3). A separate `design-system/` directory is a deprecated parallel token system — fold-or-archive undecided (§10.2). A color/token value existing in any one of the three tells you nothing about which is live on a given page — check what that page's `<body class>` and `<link>` tags actually load. |
   | **Footers** | At least three separate implementations exist: `app/templates/components/footer.html` (Jinja component), `static/js/unified-footer-loader.js` (JS-injected loader for standalone static pages), and footer markup hardcoded inline in individual templates (`base.html`, `public_base.html`, `donate.html`, and others). Confirm which one actually renders on the specific page you're touching before editing any of them — editing the component does nothing for a page using the hardcoded or JS-injected version. |
   | **`context_loop`** | Was forked into `app/modules/context_loop/service.py` and `app/services/context_loop.py`. `CONTEXT_LOOP_DECISION_BRIEF.md` claims this was resolved 2026-08-29 (service copy deleted, module copy canonical). Verify this yourself — confirm the file is actually gone and grep live (non-cached) source for the old import path — rather than trusting the doc's "Resolved" banner. Docs that say "resolved" can themselves go stale. |
   | **Feature flags** | `app/core/features.py` (DB-backed, `Feature` enum, `require_feature()`) is canonical. `app/core/feature_flags.py` (in-memory, `FeatureFlagMiddleware`) was a second, independent system with its own flag namespace. Confirm current state on the filesystem and in `app/main.py` before assuming either exists or is wired up — `AGENTS.md` Known Failure #20 and parts of `ACTIVE_CONTEXT.md` still describe both as live, which may itself be stale by the time you read this. |
   | **`gap_report.py` / `GAPS.md`** | Known to lag behind actual repo state. Any gap it reports is a hypothesis to verify against live code, never a finding to act on directly. |

   This table is a starting point, not an exhaustive list — if you find another area with the same shape (multiple parallel implementations, unclear which is live), treat it the same way: identify the canonical copy before touching either.

4. **State your confidence and what you did NOT check.** Your plan-of-action message (Step 5) must include a line naming what you verified against live code/config versus what you are taking on a doc's word. Example: "Verified against live code: `app/core/features.py` is imported in `app/main.py` and `app/core/feature_flags.py` no longer exists on disk. Not independently checked: whether `FeatureFlagMiddleware` behavior described in old handoffs is still needed anywhere — flagging as unconfirmed." Do not present a partial check as a complete one.

### Step 1b: Hard stop on unconfirmed freshness or canonicity

If, after Step 1a, you cannot confirm that:
- the file or system you're relying on is the current canonical one, **and**
- the claim you're building on is still true in the live code or data — not just in a doc,

then **STOP AND REPORT** per the master-repo standing rule (`C:\master-repo\AGENTS.md` §"STOP AND REPORT triggers") instead of proceeding on a best guess. Say exactly what you could not confirm and what would resolve it. Do not silently pick an interpretation and move forward, and do not let "I found *a* file" substitute for "I confirmed this is *the* file."

### Step 1c: Same standard for legal/statute content — Know Your Rights Library, Law Linker, state-law data

A statute number, county name, or topic matching a search or filter is **not** proof that content is current, correct, or vetted — same failure mode as the code case above, applied to data instead of code. Before serving, citing, or basing any change on Know Your Rights Library content, statute lookups, Law Linker output, or `ContextExplanationEntry` rows:

1. **Check `review_status` on the specific entry.** Only `VETTED` (or `vetted`) content may be presented as a settled answer. `BETA` (`beta`) entries are retrieval-eligible per ADR-0008 but require the lighter-weight beta disclosure — `BETA` is not evidence the content is correct, and most `context_explanation_workbook.csv` rows are currently `BETA` by design, not by oversight.
2. **Confirm the underlying legal claim was checked against a primary source** (e.g. `revisor.mn.gov`, `govinfo.gov`, official court rules) within a reasonable recency window — not just that it is present in the repo. `static/data/state-laws.json` carries a single file-level `last_updated` timestamp (stale as of the last audit — see `AUDIT_KnowYourRights_InformationIntegrity.md` Finding 1) with no per-field verification date. Do not treat that file-level timestamp as proof any individual field is current.
3. **Check whether the entry is one of the stub-only state records.** As of the last audit, only 12 of 50 states have complete `state-laws.json` data; the other 38 are stub entries (`notes` string + `stub_url`, nothing else). A match on a stub state is a placeholder, not an answer — do not present it as one. Re-verify this count yourself rather than trusting this document's number, since it too can drift.
4. **If any of the above cannot be confirmed, fall back to the generic orientation language / "not legal advice" disclaimer and flag the entry for human review.** Never present stale, unvetted, or stub content as a verified answer, even under deadline pressure. This mirrors the Information Integrity Standards already in force (sourced, opinion labeled as opinion, freshness, no presenting AI-drafted content as verified) — this step makes them a mechanical gate on this workflow instead of a policy that's easy to skip.

### Step 2: Read current state

Read these files before touching any code:

1. Read `ACTIVE_CONTEXT.md` — what is being worked on right now
2. Read `BUILD_STATE.md` — last 2 entries only (what shipped, what is broken, what is pending)
3. Read the Known Failure Registry in `AGENTS.md` — do not repeat past mistakes

### Step 2b: Claim the task

Before writing code, claim the task in the orchestrator and avoid duplicate work:

1. Master-queue task (`C:\master-repo\tools\orchestrator_state.json`): run `python C:\master-repo\tools\orchestrator_mark_task.py <task_id> in_progress --agent <agent-id> --preflight` — `--preflight` is required and attests you ran Steps 1a-1c above on this task; the claim is refused without it.
   Local-mirror task (`tools/agent_orchestrator_tasks.json`): run `python tools/mark_task_status.py <task_id> in_progress --agent <agent-id>` — prefer the master path when the task exists in both; `tools/sync_orchestrator.py` promotes mirror-only tasks to master.
2. Verify no other task with the same `file_path` is already `in_progress`
3. Do NOT edit files until the task is marked `in_progress` with `assigned_agent`/`assigned_to` set

### Step 3: Check pending Fix-It reports from admin dashboard

The admin dashboard has "Fix It" buttons that queue errors to the `admin_error_queue` Postgres table AND log a distinctive `FIXIT_REPORT|id=N|section=...|endpoint=...|priority=...|error=...` line to Render logs.

To check for pending errors the user clicked since the last session, use whatever Render log/MCP tooling is available in your assistant to search Render logs for `FIXIT_REPORT` in the last 7 days. Parse the `FIXIT_REPORT|...` lines — each is a pending issue the user wants fixed. Tell the user what was found and ask if they want to address any of them before starting new work.

If no `FIXIT_REPORT` lines found or no log tooling is available: state that plainly and continue.

### Step 4: Check the app

Run this to verify the app compiles (PowerShell, cwd repo root):

```powershell
python -m py_compile app/main.py
```text

### Step 5: State your plan

Before editing any file, tell the user:

- What you are going to change
- What file(s) you will touch
- Why this will not repeat a known failure
- The Step 1a confidence statement: what you verified against live code/config/data, and what you did NOT check and are taking on a doc's word

### Step 6: After making changes

Verify changed files compile:

```powershell
python -m py_compile app/main.py app/core/navigation.py
```

Then update `BUILD_STATE.md` with what changed.

---

## Revision log

**2026-09-14 — added Steps 1a/1b/1c (freshness & canonicity gate).** See `.devin/skills/preflight/SKILL.md` for the full changelog — this file mirrors that skill and must stay in sync.
