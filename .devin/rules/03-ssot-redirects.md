---
description: SSOT navigation and redirect rules
---

# SSOT Navigation and Redirects

All internal navigation must use the Single Source of Truth (SSOT) registry.

## Hard rules

- **NEVER** hardcode URL strings in Python or templates.
- **NEVER** return `RedirectResponse(url="/some/path")` directly.
- **ALWAYS** use `navigation.get_stage("stage_name")` and `ssot_redirect()` from `app.core.ssot_guard`.
- Mark external OAuth redirects as exempt from SSOT guard where appropriate.

## Pattern

```python
from app.core.navigation import navigation
from app.core.ssot_guard import ssot_redirect

providers_stage = navigation.get_stage("providers")
providers_path = providers_stage.path if providers_stage else "/storage/providers"
return ssot_redirect(providers_path, context="route_name scenario")
```

## Security

- Storage gate must use server-side, tamper-proof signals only:
  - HMAC-signed `semdrive_provider` cookie.
  - Provider code embedded in the signed `user_id` cookie, verified via `parse_user_id()`.
- Never rely on client-spoofable headers such as `x-storage-connected`.
- Use `parse_user_id()` from `app.core.user_id` for all user ID parsing.

## Historical fixes

- `app/routers/role_ui.py` — converted to SSOT redirects and secure storage gate.
- `app/routers/storage.py`, `app/routers/auth.py`, `app/routers/onboarding.py` — 24 `RedirectResponse` calls converted to SSOT.
- `app/routers/document_delivery.py` — missed hardcoded `/storage/providers` redirect fixed.
