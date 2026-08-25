---
name: ship
description: Verify, compile, test, commit, and push all work to main so Render deploys it
---

# Skill

## /ship — End of Session Deploy Checklist

Run this at the end of EVERY work session. Do not close the IDE until this completes clean.

---

### Step 0 — Confirm you are in the checkout that actually has your changes

**Do not assume a fixed path is the correct working checkout.** This project has more than one
local git checkout of the same repo on disk (e.g. `modules\app-semptify-fastapi` vs.
`sources\app-semptify-fastapi`), and they can diverge — one may be stale and contain none of the
current session's edits. Shipping from the wrong one commits/pushes nothing real while looking
like it succeeded. (This exact mistake was caught and fixed 2026-08-25 — see BUILD_STATE.md.)

1. Identify the directory where you actually made edits this session (the `cwd` you used for
   `edit`/`write` calls, not a value copied from an old doc).
2. Run `git status --short` in that directory and confirm it lists the files you actually
   changed this session. If it shows nothing, or shows unrelated/unfamiliar changes, STOP —
   you are in the wrong checkout. Find the correct one before proceeding.
3. Use that confirmed directory as `<repo_root>` for every step below. Per master-repo
   `AGENTS.md`, `modules/<name>/` is the correct day-to-day working checkout; `sources/<name>/`
   is a canonical reference copy and should not be edited or shipped from directly.

---

### Step 1 — Compile check all core files

Run: `.\venv311\Scripts\Activate.ps1; python -m py_compile app/main.py app/core/navigation.py app/modules/vault/router.py app/modules/onboarding/router.py app/modules/documents/router.py app/services/vault_upload_service.py <any other files you changed this session>; echo "ALL OK"` in cwd `<repo_root>`

If any file fails to compile, STOP and fix it before proceeding.

---

### Step 2 — Run Playwright tests (if server is running)

Check if a dev server is running on port 8000. If yes, run the Playwright test suite:

Run: `node run.js C:/tmp/playwright-test-semptify.js` in cwd `C:/Users/bradc/.agents/skills/playwright`

If the test file does not exist at `/tmp/playwright-test-semptify.js`, skip this step and note it in the commit message.
All tests must pass before proceeding. Fix any failures first.

---

### Step 3 — Check what is uncommitted

Run: `git status --short` in cwd `<repo_root>`

Review the output with the user. Ask: "Are there any files in this list that should NOT be committed (temp files, test output, secrets)?"

Do NOT stage:

- `*.log`, `*.db`, `.env`, `__pycache__/`
- `test_results.txt`, `server_*.log`
- `data/test_local_vault/`, `recipe_visualizations/`
- Any file containing secrets or tokens
- Any temporary/scratch files created during the session's own verification work (e.g. `tools/_tmp_*.py`) — delete these before staging, don't ship them

---

### Step 4 — Stage only the files this session actually changed

Prefer staging the specific files this session touched over a blanket `git add app/ static/ ...` —
review `git status --short` from Step 3 and stage exactly what belongs to this session's task
(one task per commit, per standing rule).

Run: `git add <specific files from Step 3>` in cwd `<repo_root>`

---

### Step 5 — Commit with a clear message

Ask the user: "What did we accomplish this session?"

Write a commit message in this format:

```text
<one-line summary of the session>

- <file>: <what changed and why>
- <file>: <what changed and why>
```

Check `docs/doc-map.yaml` / the pre-commit hook output — some paths require the subject line to
start with `admin:`, `user:`, `help:`, or `adr:`. If the commit is rejected for this reason,
prefix the subject accordingly and retry.

Run: `git commit -m "<message>"` in cwd `<repo_root>`

---

### Step 6 — Push to the real GitHub remote

**Do not assume the remote named `origin` points at GitHub.** Some checkouts (e.g.
`modules\app-semptify-fastapi`) have `origin` pointing at a local path (another checkout on
disk), with the actual GitHub remote under a different name (e.g. `github-direct`).

1. Run `git remote -v` in cwd `<repo_root>` and identify the remote whose URL is
   `https://github.com/1semptify-arch/Semptify.git` — use that remote name for the push, not
   whichever is literally named `origin`.
2. Run: `git push <github-remote-name> main` in cwd `<repo_root>`.
3. **If the push is rejected with a branch-protection error** (`GH013: Repository rule
   violations`, "Changes must be made through a pull request"): do not force-push or bypass
   this. Instead:
   - `git checkout -b <descriptive-branch-name>`
   - `git push <github-remote-name> <descriptive-branch-name>`
   - `gh pr create --repo 1semptify-arch/Semptify --base main --head <descriptive-branch-name> --title "<title>" --body "<summary + test plan>"`
   - Report the PR URL to the user and STOP. Do not merge it yourself — the user reviews and
     merges via the GitHub UI.
   - Switch back to `main` locally (`git checkout main`) once the branch is pushed.

---

### Step 7 — Confirm pushed

Run: `git log --oneline -3` in cwd `<repo_root>` (if pushed directly to main), or
`gh pr view <number> --repo 1semptify-arch/Semptify --json number,title,url,mergeable` (if a PR
was opened).

Tell the user either:
- "Render is now deploying commit [hash]. Check <https://dashboard.render.com> to watch the deploy log." (direct push case), or
- "Opened PR #[number] at [url] — branch protection requires review before this reaches main and deploys." (PR case)

---

### Step 8 — Update BUILD_STATE.md

Update `<repo_root>\BUILD_STATE.md` with:

- Last deployed commit hash (or PR number if not yet merged) and date/time
- What was shipped this session
- What is known working
- What is known broken or pending
- What the next session should start with

If pushing directly succeeded, commit this separately:
Run: `git add BUILD_STATE.md && git commit -m "docs: update BUILD_STATE after session ship" && git push <github-remote-name> main` in cwd `<repo_root>`

If a PR was opened in Step 6, fold the BUILD_STATE.md update into that same PR instead of a
separate direct-to-main commit (it will also be blocked by branch protection).

---

### Step 9 — Final confirmation

Tell the user the session is complete with:

- Commit hash(es) pushed, or PR URL(s) opened for review
- Render deploy URL (once merged)
- Summary of what was shipped
- What to pick up next session
