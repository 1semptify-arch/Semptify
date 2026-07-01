---
description: Mandatory pre-flight check - run this before starting any work session
---

## Semptify Pre-Flight Check

Run this at the start of EVERY session. No exceptions.

### Step 0: Semptify is NOT a business model — Read this first
Semptify is a **public utility, not a product.** Read `CORE_CONTEXT.md` in the repo root before writing or approving any copy, UI text, or feature. Enforce these rules:

- **North star metric: Time to Real Help.** Not sessions. Not return visits. Not engagement. Not signups. Every feature either reduces Time to Real Help or it doesn't belong.
- **NEVER use the word "free"** on any page, button, label, or description. Saying "free" insinuates we charge for other things. We don't. We never have. We never will.
- **NEVER use business-model terminology** — no "accounts", "log in", "sign up", "subscription", "upgrade", "premium", "paid plan", "trial", "pricing", or similar. These words imply a commercial product. Semptify is not one.
- **No advertising — ever.** No banner ads, no sponsored content, no affiliate links, no tracking pixels for ad networks. This is non-negotiable and permanent.
- **Listing vs advertising — there is a difference.** A *listing* is a neutral directory entry of a resource (e.g., "HOME Line MN — 612-728-5767"). An *advertisement* is promotional content paid for or placed to generate revenue/clicks for the advertiser's benefit. Listings are permitted only when:
  - The resource is directly relevant to tenant housing rights
  - The user (project owner) has reviewed and approved the specific listing
  - The listing is neutral, factual, and non-promotional
  - **When in doubt, do NOT add the listing. Ask the user first.**
- **There must never be a dead end.** Every error page, every broken flow, every moment of confusion must route the user toward real help. Not leave them hanging.
- **If you see existing text that violates these rules**, flag it to the user and propose a fix. Do not silently leave it.

### Step 1: Read current state
Read these files before touching any code:
1. Read `ACTIVE_CONTEXT.md` — what is being worked on right now
2. Read `BUILD_STATE.md` — last 2 entries only (what shipped, what is broken, what is pending)
3. Read the Known Failure Registry in `AGENTS.md` — do not repeat past mistakes

### Step 2: Check pending Fix-It reports from admin dashboard
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

### Step 3: Check the app
// turbo
Run this to verify the app compiles:
```powershell
cd c:\Semptify\Semptify-FastAPI; python -m py_compile app/main.py
```

### Step 4: State your plan
Before editing any file, tell the user:
- What you are going to change
- What file(s) you will touch
- Why this will not repeat a known failure

### Step 5: After making changes
// turbo
Verify changed files compile:
```powershell
cd c:\Semptify\Semptify-FastAPI; python -m py_compile app/main.py app/core/navigation.py
```

Then update `BUILD_STATE.md` with what changed.
