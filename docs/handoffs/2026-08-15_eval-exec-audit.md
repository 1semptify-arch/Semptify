# HANDOFF: eval()/exec() Security Classification

## Scope (one task only — do not expand)
Audit the three flagged `eval()`/`exec()` call sites from the app_crawler.py run. For each, determine whether the evaluated/executed string can be influenced — directly or indirectly — by untrusted input (uploaded file content, filenames, user-submitted form/API fields, query params). Classify each site as SAFE or UNSAFE. Do not modify code in this task. Do not "clean up while you're in there."

## Preflight (required before touching anything)
- Read the full file for each of the three targets below, not just the flagged line — read enough surrounding context to trace where the evaluated string originates.
- Trace the call chain backward: what function calls this code, and where does *that* data come from? Follow it back to the nearest point where it's either (a) a hardcoded/config-defined string, or (b) something that touched a request, upload, or file parse.
- Do not assume "internal tool" or "admin-only" means safe — note the assumption explicitly if you're relying on it, so Brad can confirm.

## Targets
1. `file_validator.py` — flagged eval()/exec() usage
2. `testing_framework.py` — flagged eval()/exec() usage
3. `router.py` — flagged eval()/exec() usage

## Per-site output format (paste this back, one block per file)

```
FILE: <path>:<line>
CALL: eval() | exec()
EVALUATED EXPRESSION: <the actual string/expression being passed>
DATA ORIGIN: <trace result — where does this string ultimately come from>
UNTRUSTED PATH EXISTS: yes/no
REASONING: <1-3 sentences>
CLASSIFICATION: SAFE | UNSAFE | NEEDS BRAD INPUT
```

## Hard gate
- If ANY site is classified UNSAFE, STOP. Do not attempt a fix in this task. Open a separate ticket describing the exploit path (what input, what it reaches, what it could do) and wait for a follow-up handoff scoped to the fix.
- If a site is ambiguous (e.g., depends on deployment config, or on whether an "admin-only" route is actually gated correctly), classify as NEEDS BRAD INPUT rather than guessing SAFE.
- Do not self-approve. This is a read/report task — commit only the report, not code changes.

## Out of scope for this task
- vault-portal.html upload stub
- journal.html delete endpoint
- fetch() catch handler gaps
- pytest suite hang investigation

These are separate tasks and will get their own handoffs.
