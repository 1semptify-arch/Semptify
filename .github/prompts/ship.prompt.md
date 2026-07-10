---
mode: agent
description: Verify, compile, test, commit, and push all work to main so Render deploys it
---

<!-- Mirrors .devin/workflows/ship.md — keep both in sync when editing. -->

## /ship — End of Session Deploy Checklist

Run this at the end of EVERY work session. Do not close the IDE until this completes clean.

---

### Step 1 — Compile check all core files
Run: `.\venv311\Scripts\Activate.ps1; python -m py_compile app/main.py app/core/navigation.py app/modules/vault/router.py app/modules/onboarding/router.py app/modules/documents/router.py app/services/vault_upload_service.py; echo "ALL OK"` in cwd repo root.

If any file fails to compile, STOP and fix it before proceeding.

---

### Step 2 — Run Playwright tests (if server is running)
Check if a dev server is running on port 8000. If yes, run the Playwright test suite (see `tests/` or the `playwright` skill for the current runner path). If no test runner is configured, skip this step and note it in the commit message. All tests must pass before proceeding. Fix any failures first.

---

### Step 3 — Check what is uncommitted
Run: `git status --short` in cwd repo root.

Review the output with the user. Ask: "Are there any files in this list that should NOT be committed (temp files, test output, secrets)?"

Do NOT stage:
- `*.log`, `*.db`, `.env`, `__pycache__/`
- `test_results.txt`, `server_*.log`
- `data/test_local_vault/`, `recipe_visualizations/`
- Any file containing secrets or tokens

---

### Step 4 — Stage all application files
Stage only: `app/`, `static/`, `tests/`, `scripts/`, `alembic/`, and root config files.

Run: `git add app/ static/ tests/ scripts/ alembic/ render.yaml Dockerfile requirements.txt pyproject.toml AGENTS.md BUILD_STATE.md ACTIVE_CONTEXT.md` in cwd repo root.

---

### Step 5 — Commit with a clear message
Ask the user: "What did we accomplish this session?"

Write a commit message in this format:
```
<one-line summary of the session>

- <file>: <what changed and why>
- <file>: <what changed and why>
```

Run: `git commit -m "<message>"` in cwd repo root.

---

### Step 6 — Push to main
Run: `git push origin main` in cwd repo root.

---

### Step 7 — Confirm pushed
Run: `git log --oneline -3` in cwd repo root.

Verify the latest commit hash appears at HEAD. Tell the user:
"Render is now deploying commit [hash]. Check https://dashboard.render.com to watch the deploy log."

---

### Step 8 — Update BUILD_STATE.md
Update `BUILD_STATE.md` with:
- Last deployed commit hash and date/time
- What was shipped this session
- What is known working
- What is known broken or pending
- What the next session should start with

Commit BUILD_STATE.md update separately:
Run: `git add BUILD_STATE.md && git commit -m "docs: update BUILD_STATE after session ship" && git push origin main` in cwd repo root.

---

### Step 9 — Final confirmation
Tell the user the session is complete with:
- Commit hash(es) pushed
- Render deploy URL
- Summary of what was shipped
- What to pick up next session
