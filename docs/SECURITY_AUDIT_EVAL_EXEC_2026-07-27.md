# Security Audit: eval()/exec() Call Sites

**Date:** 2026-07-27
**Scope:** Classify the three `eval()`/`exec()` call sites flagged by `tools/app_crawler.py`.
**Method:** Read each file's surrounding context and trace the evaluated/executed string back to its origin.
**Outcome:** No unsafe reachable call sites were found. Two of the three "flags" are pattern-matching strings, not actual `eval()`/`exec()` calls. The remaining `exec()` call operates only on hardcoded `test_code` strings.

---

## FILE: `app/core/file_validator.py:432-433`

**CALL:** Neither — these lines are byte-string literals, not function calls.

**EVALUATED EXPRESSION:** `b'eval('` and `b'exec('` are entries in the `script_patterns` list inside `_has_script_content()`.

**DATA ORIGIN:** Hardcoded detection patterns. `_has_script_content()` scans uploaded `file_content` (bytes) for these substrings and returns `True` if any are found.

**UNTRUSTED PATH EXISTS:** No.

**REASONING:** The file validator does not execute `eval()` or `exec()`; it searches binary file content for the literal strings as part of malware/script-content detection.

**CLASSIFICATION:** SAFE

---

## FILE: `app/core/testing_framework.py:354`

**CALL:** `exec(code, local_vars)`

**EVALUATED EXPRESSION:** `test_case.test_code` (also `setup_code` and `teardown_code` in the same `_execute_code` method).

### DATA ORIGIN:

- `test_code` values are hardcoded Python strings inside `app/core/testing_framework.py` (module-level default suites) and inside `app/modules/testing/router.py` (the `/suites` endpoint branches on `request.tags` such as `"core"`, `"security"`, `"performance"`).
- The public `TestSuiteCreateRequest` schema only accepts `suite_id`, `name`, `description`, and `tags`; it does **not** accept a `test_cases` list or any `test_code` field.
- No other route or caller in the current codebase constructs a `TestCase` from request/form/query data.

**UNTRUSTED PATH EXISTS:** No — in the current code, the executed string never originates from user input, uploads, filenames, or query parameters.

**REASONING:** The only `exec()` call site runs hardcoded test snippets that are either statically defined at module load or selected by tag in the `/suites` endpoint. The `local_vars` dictionary restricts the visible names to `datetime`, `timezone`, `logger`, and `asyncio`, but because `__builtins__` is not explicitly removed, the sandbox is weak. If any future code path creates a `TestCase` from user-supplied text, that code would execute with full builtins access.

**CLASSIFICATION:** SAFE (with hardening note: the `exec()` environment should be sandboxed with `{"__builtins__": {}}` to guard against future misuse.)

---

## FILE: `app/modules/development/router.py:435-445`

**CALL:** Neither — these lines are string-membership checks, not function calls.

**EVALUATED EXPRESSION:** `"eval(" in content` and `"exec(" in content` are checks inside the `analyze_security()` helper.

**DATA ORIGIN:** `content` is the text of every `*.py` file found under `target_path` (default: `app/modules/development/router.py`'s grandparent directory). The helper opens each file, reads it, and records security issues if the substrings appear.

**UNTRUSTED PATH EXISTS:** No.

**REASONING:** `analyze_security()` only reads source files on disk and appends findings to a list; it never calls `eval()` or `exec()` on the file contents.

**CLASSIFICATION:** SAFE

---

## Summary

| File | Actual call? | Evaluated string origin | Untrusted path? | Classification |
| ------ | -------------- | ------------------------ | ----------------- | ---------------- |
| `app/core/file_validator.py:432-433` | No | Hardcoded byte-string patterns | No | SAFE |
| `app/core/testing_framework.py:354` | Yes (`exec`) | Hardcoded `TestCase` code strings | No | SAFE (harden recommended) |
| `app/modules/development/router.py:435-445` | No | Source-file content read from disk | No | SAFE |

No site is currently exploitable via untrusted input. The only genuine `exec()` call should be hardened so that a future route or helper cannot accidentally pass user-controlled strings into it.
