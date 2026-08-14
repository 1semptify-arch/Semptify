---
name: preflight
description: Mandatory pre-flight check - run this before starting any work session
---

# Skill

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
do not touch it

### Step 1: Prove you know Semptify — NO LAZY WORK

**Before you touch a single file, you must demonstrate working knowledge of this system.** If you cannot answer these from the docs, you are not ready to write code. Go back and read until you can.

Read ALL of the following — not skim, READ:

1. `AGENTS.md` — Full document including Known Failure Registry (all 16 items)
2. `PROJECT_BIBLE.md` — Governance, gate chain, onboarding flow, doc hierarchy
3. `docs/MOTIVATIONS.md` — Foundational motivations, language rules, Information Integrity Standards
4. `docs/adr/0001`–`0006` — Permanent decisions (storage, navigation, attraction, banned motivations, language, open access)
5. `BUILD_GUIDE_SSOT.md` — Build philosophy, active features, SSOT rules
6. `CORE_CONTEXT.md` — What Semptify IS, who it's for, what we never build

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

### Step 2: Read current state

Read these files before touching any code:

1. Read `ACTIVE_CONTEXT.md` — what is being worked on right now
2. Read `BUILD_STATE.md` — last 2 entries only (what shipped, what is broken, what is pending)
3. Read the Known Failure Registry in `AGENTS.md` — do not repeat past mistakes

### Step 2b: Claim the task

Before writing code, claim the task in the orchestrator and avoid duplicate work:

1. Run `python tools/mark_task_status.py <task_id> in_progress --agent <agent-id>`
2. Verify no other task with the same `file_path` is already `in_progress`
3. Do NOT edit files until the task is marked `in_progress` with `assigned_agent` set

### Step 3: Check pending Fix-It reports from admin dashboard

The admin dashboard has "Fix It" buttons that queue errors to the `admin_error_queue` Postgres table AND log a distinctive `FIXIT_REPORT|id=N|section=...|endpoint=...|priority=...|error=...` line to Render logs.

To check for pending errors the user clicked since the last session:

1. Call `mcp3_list_workspaces` (select the workspace if not already selected)
2. Call `mcp3_list_services` to get the Semptify service ID
3. Call `mcp3_list_logs` with:
   - `resource`: ["<service_id>"]
   - `level`: ["info"]
   - `text`: ["FIXIT_REPORT"]
   - `limit`: 20
   - `startTime`: 7 days ago (e.g., "2026-06-13T00:00:00Z")
4. Parse the `FIXIT_REPORT|...` lines — each is a pending issue the user wants fixed
5. Tell the user: "Found N pending Fix-It reports from the admin dashboard:" and list them
6. Ask if they want to address any of them before starting new work

If no FIXIT_REPORT lines found: "No pending Fix-It reports. Admin dashboard is clean."

### Step 4: Check the app

// turbo
Run this to verify the app compiles:

```powershell
cd c:\Semptify\Semptify-FastAPI; python -m py_compile app/main.py
```text

### Step 5: State your plan

Before editing any file, tell the user:

- What you are going to change
- What file(s) you will touch
- Why this will not repeat a known failure

### Step 6: After making changes

// turbo
Verify changed files compile:

```powershell
cd c:\Semptify\Semptify-FastAPI; python -m py_compile app/main.py app/core/navigation.py
```

Then update `BUILD_STATE.md` with what changed.
