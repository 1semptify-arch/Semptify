# HANDOFF: Two Independent Tasks (separate commits — do not combine)

This doc bundles two follow-up items from the eval/exec audit and the earlier full-suite run. They are unrelated to each other. Complete, commit, and mark status separately. Do not let one PR touch both files.

---

## TASK 1 — Harden exec() in testing_framework.py

### Context
`app/core/testing_framework.py:354` calls `exec(code, local_vars)` against `test_case.test_code` / `setup_code` / `teardown_code`. Audit (SECURITY_AUDIT_EVAL_EXEC_2026-07-27.md) confirmed these strings are hardcoded today — no request field on `/suites` or elsewhere feeds untrusted input into them — but the exec environment does not restrict `__builtins__`. This is a latent risk: safe only because nothing untrusted reaches it *today*.

### Scope
- Restrict `__builtins__` in the `exec()` call at `testing_framework.py:354` so the executed test code cannot access dangerous builtins (file I/O, `import`, `os`, `subprocess`, etc.) beyond what test cases legitimately need.
- Preferred approach: pass a restricted `local_vars`/`globals` dict with `__builtins__` set to an explicit allow-list, rather than the full builtins module. If a full sandboxing library (e.g. RestrictedPython) is already a dependency elsewhere in the repo, prefer reusing it over a hand-rolled allow-list; otherwise a hand-rolled allow-list is fine for this scope.
- Add a code comment directly above the `exec()` call stating: this executes hardcoded test-case strings only; if any future code path allows request-supplied test_code/setup_code/teardown_code, this sandboxing must be revisited and the audit re-run.

### Explicitly out of scope
- Do not touch `router.py` or `file_validator.py` — both were classified SAFE with no changes needed.
- Do not add new test-authoring features or change how test cases are defined/loaded.
- Do not attempt to sandbox anything outside this one exec() call.

### Verification
- Run the existing testing_framework test cases (if any exist) to confirm hardcoded test/setup/teardown code still executes correctly post-change.
- Confirm a deliberately dangerous string (e.g. `__import__('os').system('echo test')`) is blocked when passed through the same exec() call, as a manual smoke test — do not leave this test string committed anywhere.

### Commit
One commit, scoped only to `testing_framework.py`. No self-approval.

---

## TASK 2 — Investigate full pytest suite collection/execution hang

### Context
`python -m pytest tests -q --no-cov` hung at ~35–41% and had to be killed. `conftest.py` imports `app.main`, which triggers background service initialization (job processor, websocket manager). This appears to make full-suite collection/startup unstable. Targeted subsets (test_ssot_architecture.py, test_resource_directory.py, test_media_capture.py, test_litigation_intelligence_graph.py, test_litigation_intelligence_reporting.py, test_document_delivery_service.py, test_manager_dashboard.py) all pass individually.

### Scope
- Identify why importing `app.main` inside `conftest.py` triggers live background services (job processor, websocket manager) during test collection rather than only at real app runtime.
- Determine whether these services can be:
  - deferred behind an app-factory pattern (only instantiated when the app actually starts, not on import), or
  - mocked/stubbed specifically for the test environment via a pytest fixture, or
  - guarded by an environment flag (e.g. `TESTING=1`) that `app.main` checks before starting them.
- Do not restructure `app.main` broadly — this task is scoped to isolating test collection from live service startup, not a general refactor.

### Investigation output (required before any fix)
Produce a short root-cause note answering:
1. Exactly which line(s) in `app.main` (triggered via `conftest.py` import) start the job processor and websocket manager.
2. Why these don't hang when tests are run as targeted subsets — is it timing, resource contention across parallel test files, or something specific to particular test modules combined with the background services?
3. Confirmation of whether background services are thread-based, asyncio-based, or subprocess-based, since that determines the right isolation approach.

### Fix scope (only after root cause is confirmed — check in before proceeding if the fix requires touching app.main's startup sequence broadly)
- Preferred fix: gate background service startup behind a check (e.g. `if not os.environ.get("TESTING")`) so `conftest.py` can set that flag before import.
- If that's not feasible without deeper changes, stop and report back rather than attempting a larger refactor under this task.

### Explicitly out of scope
- Do not modify the individual test files that currently pass.
- Do not change `guardrail_engine.py` or `sync_orchestrator.py`.
- Do not attempt to fix this by simply increasing timeouts or adding `pytest-timeout` skips — that masks the hang rather than resolving it.

### Commit
One commit for the root-cause note (even if no fix yet). A second, separate commit for the fix once approved. No self-approval on either.

---

## General reminders (apply to both tasks)
- Preflight read the full relevant files before editing.
- One task per commit — Task 1 and Task 2 must not land in the same commit.
- If either task turns up something unexpected outside its stated scope, stop and report rather than expanding the task.
