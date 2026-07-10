---
mode: agent
description: Mandatory pre-flight check - run this before starting any work session
---

<!-- Mirrors .devin/workflows/preflight.md — keep both in sync when editing. -->

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

### Step 1: Read current state
Read these files before touching any code:
1. Read `ACTIVE_CONTEXT.md` — what is being worked on right now
2. Read `BUILD_STATE.md` — last 2 entries only (what shipped, what is broken, what is pending)
3. Read the Known Failure Registry in `AGENTS.md` — do not repeat past mistakes

### Step 2: Check pending Fix-It reports from admin dashboard
The admin dashboard has "Fix It" buttons that queue errors to the `admin_error_queue` Postgres table AND log a distinctive `FIXIT_REPORT|id=N|section=...|endpoint=...|priority=...|error=...` line to Render logs.

To check for pending errors the user clicked since the last session, use whatever Render log/MCP tooling is available in your assistant to search Render logs for `FIXIT_REPORT` in the last 7 days. Parse the `FIXIT_REPORT|...` lines — each is a pending issue the user wants fixed. Tell the user what was found and ask if they want to address any of them before starting new work.

If no `FIXIT_REPORT` lines found or no log tooling is available: state that plainly and continue.

### Step 3: Check the app
Run this to verify the app compiles (PowerShell, cwd repo root):
```powershell
python -m py_compile app/main.py
```

### Step 4: State your plan
Before editing any file, tell the user:
- What you are going to change
- What file(s) you will touch
- Why this will not repeat a known failure

### Step 5: After making changes
Verify changed files compile:
```powershell
python -m py_compile app/main.py app/core/navigation.py
```

Then update `BUILD_STATE.md` with what changed.
