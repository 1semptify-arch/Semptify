---
description: Mandatory pre-flight check - run this before starting any work session
---

## Semptify Pre-Flight Check

Run this at the start of EVERY session. No exceptions.

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
