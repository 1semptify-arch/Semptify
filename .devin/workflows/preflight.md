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
