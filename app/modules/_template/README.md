# Template Module

> **Replace this entire directory** with your module's implementation.
> This is the scaffold for new internal dev modules (Phase 3.4).

## Maturity Checklist

See `ROADMAP_TO_PUBLIC_RELEASE.md` §3.3 for full details.

- [ ] **dev_only** — Just code, no tests, no docs. Admin-only visibility.
- [ ] **experimental** — Has unit tests, has basic docs, works in isolation. Admin + opt-in.
- [ ] **beta** — Has integration tests, has user docs, works with other modules, registered in `FunctionGroupContract`. Admin + beta-flag users.
- [ ] **stable** — Has E2E tests, has admin docs, used by real users, monitored for errors. All applicable roles.

## Files

| File | Purpose |
| ------ | --------- |
| `router.py` | FastAPI endpoints (keep thin) |
| `service.py` | Business logic (async by default) |
| `models.py` | Pydantic request/response models |
| `register.py` | Module registration helper |
| `tests/` | Unit + integration tests |

## Getting Started

1. Copy this directory to `app/modules/<your_module>/`
2. Replace "template" / "Template" in all files with your module name
3. Register in `app/core/product_manifest.py` with `lifecycle='dev_only'`
4. Implement your router + service + models
5. Write tests in `tests/`
6. Use the dev_lab UI at `/dev/lab/<your_module>` to track maturity

## Conventions

- **Routers are thin** — delegate to `service.py`
- **Async by default** — all I/O operations are async
- **Use `utc_now()`** from `app.core.utc` — never `datetime.now()`
- **Use `get_request_user_id(request)`** from `app.core.request_utils` for user ID
- **Specific exceptions** — never bare `except:`
- **Pydantic models** for all request/response bodies
