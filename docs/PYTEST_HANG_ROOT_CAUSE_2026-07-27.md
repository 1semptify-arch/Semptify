# Pytest Full-Suite Hang — Root Cause Analysis

**Date:** 2026-07-27
**Reporter:** Devin
**Status:** Root cause confirmed; fix implemented in follow-up commit

## Summary

The full-suite hang was **not** caused by `app.main` starting the job processor or WebSocket manager at import time. Those services are lazy-started by their respective `get_*()` factories and only run when routes/explicit calls use them. The hang was caused by **`tests/test_all_endpoints.py`** executing live HTTP requests to `http://localhost:8000` at **module import time**. With the server not running, each request waited for its 10-second `requests` timeout, so pytest collection/execution appeared to hang.

## Answers to the investigation questions

### 1. Which lines in `app.main` start the job processor and websocket manager?

**They are not started by `app.main` at import time.**

- `app/core/job_processor.py:465-476` defines `get_job_processor()`, which lazily instantiates and starts `JobProcessor` worker threads the first time it is called.
- `app/core/websocket_manager.py:456-464` defines `get_websocket_manager()`, which lazily instantiates the manager the first time it is called.
- Both modules register `atexit` handlers at the bottom of their files:
  - `app/core/job_processor.py:822-823`: `atexit.register(lambda: get_job_processor().stop())`
  - `app/core/websocket_manager.py:492-493`: `atexit.register(lambda: asyncio.run(get_websocket_manager().shutdown()))`
- These `atexit` handlers run when the Python process exits. They *do* start the job processor just to stop it, which is wasteful and produces the `ValueError: I/O operation on closed file` logging errors seen at the end of every pytest run, but they do not cause a hang.

### 2. Why doesn't the hang occur on targeted test subsets?

The targeted subsets (e.g., `test_ssot_architecture.py`, `test_manager_dashboard.py`, `test_document_delivery_service.py`, etc.) do not import or collect `tests/test_all_endpoints.py`. That file is the only root test file that performs live network I/O at module level, so its requests are only executed when the whole `tests/` tree is collected.

### 3. What kind of background services are these?

- **Job processor:** `threading.Thread` daemon worker pool (4 workers by default) plus optional retry threads.
- **WebSocket manager:** Pure `asyncio` background tasks (broadcast/cleanup loops) created on demand.
- **Log flusher / performance monitor:** Also started, but only inside the FastAPI lifespan, not at module import.

## Actual hang location

- **File:** `tests/test_all_endpoints.py`
- **Behavior:** Top-level `test("...", lambda: get("/..."))` and `test("...", lambda: post("/...", ...))` calls fire `requests.get` / `requests.post` to `http://localhost:8000` as the module is imported.
- **Trigger:** Running `python -m pytest tests` causes pytest to import this module during collection.
- **Symptom:** Each unanswerable request waits 10 seconds; dozens of endpoints accumulate to many minutes, appearing as a hang at ~35-41% progress.

## Recommended fix (implemented in follow-up commit)

1. Wrap the module-level execution in `tests/test_all_endpoints.py` inside `if __name__ == "__main__":` so the requests only run when the script is executed manually, not when pytest imports it for collection.
2. Harden the `atexit` handlers in `app/core/job_processor.py` and `app/core/websocket_manager.py` so they only call `.stop()` / `.shutdown()` if the singleton has actually been instantiated. This eliminates the wasteful start/stop cycle and the `I/O operation on closed file` logging errors at pytest exit.

## Verification after fix

- `python -m pytest tests --ignore=tests/e2e --ignore=tests/integration -q --no-cov` completes in ~26.5 minutes without hanging.
- Result: **986 passed, 149 skipped, 67 failed** — failures are pre-existing endpoint/auth/MockWebSocket issues unrelated to the hang.
