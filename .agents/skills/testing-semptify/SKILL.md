---
name: testing-semptify
description: How to run Semptify tests locally, authenticate test clients, and avoid common Windows environment pitfalls.
---

# Semptify Local Testing Guide

## Running the Page Composer tests

```bash
pytest tests/test_page_composer_render.py -q
```

This file requires a valid signed `semptify_uid` cookie and an in-memory OAuth token (see below).

## Authenticated test client setup

The `authenticated_client` fixture in `tests/conftest.py` now:

- Uses a non-test `user_id` such as `GUowner123` (`G` = Google Drive, `U` = tenant/user, 8 random chars).
- Signs the `semptify_uid` cookie with `app.core.cookie_auth.sign_user_id`.
- Seeds `app.core.oauth_token_manager.token_manager` with a mock `OAuthToken` so `auth_gate` and token refresh resolve without calling real providers.

The user ID must **not** start with any of these prefixes (blocked by `app.core.security.is_valid_user_storage`):
`open-mode`, `system`, `su`, `test`, `demo`, `admin-`, `guest`.

## HTTPException response shape

`app.main` registers `app.core.error_handling.semptify_exception_handler` globally. FastAPI/Starlette `HTTPException` responses are wrapped:

```json
{
  "success": false,
  "error": {
    "code": "HTTP_ERROR",
    "message": "Unknown subject: not-a-subject"
  }
}
```

Tests should assert against `response.text` or `response.json()["error"]["message"]` rather than `response.json()["detail"]`.

## Windows environment pitfall: python-magic

`python-magic` may install a Cygwin `libmagic` DLL that crashes the process at import with `TP_NUM_C_BUFS too small: 50`. The app guards every `import magic` with `try/except ImportError`, so the app is functional without it. On Windows test runners either:

- Uninstall `python-magic` from the active venv, or
- Install a native MSVC build of `libmagic`/`magic.dll`.

## Required environment for local runs

```bash
export DATABASE_URL="sqlite+aiosqlite:///./test.db"
export SECURITY_MODE="open"
export SECRET_KEY="replace-with-local-secret"  # pragma: allowlist secret
```

Or on Windows PowerShell:

```powershell
$env:DATABASE_URL="sqlite+aiosqlite:///./test.db"
$env:SECURITY_MODE="open"
$env:SECRET_KEY="replace-with-local-secret"  # pragma: allowlist secret
```
