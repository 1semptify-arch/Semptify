# Example External Module

> **Replace this template** with your external module's implementation.
> This is the scaffold for third-party developers (Phase 3.5).

## Manifest

The `semptify.module.json` file declares:
- **name** — unique module name (lowercase, hyphens)
- **vendor** — your organization name
- **version** — semver
- **lifecycle** — `dev_only` → `experimental` → `beta` → `stable`
- **permissions** — what your module can do (least privilege!)
- **dependencies** — which SDK clients you need
- **entry_point** — `router.py:router` (file:attribute)
- **content_hash** — SHA-256 of all .py files (computed by `external_loader`)

## Available SDK Clients

| Client | Permission | Description |
|--------|------------|-------------|
| `VaultClient` | `vault.read` / `vault.write` | Read/write user's vault files |
| `TimelineClient` | `timeline.read` / `timeline.write` | Read/create timeline events |
| `OverlayClient` | `overlay.read` / `overlay.write` | Read/create overlays |
| `DocumentClient` | `document.read` / `document.write` | Read/upload documents |
| `NotificationClient` | `notification.send` | Send notifications to users |

## Allowed Imports

- `app.sdk.external.*` — all SDK clients
- `app.sdk.vault.*` — vault folder specs
- `fastapi`, `pydantic`, `starlette`
- Standard library: `typing`, `datetime`, `dataclasses`, `enum`, `json`, `logging`, `pathlib`

## Forbidden Imports

These will cause `ExternalModuleSecurityError` at load time:
- `app.core.database`, `app.core.redis`, `app.core.security`
- `app.services.*` (except via SDK clients)
- `app.modules.*` (other internal modules)
- `app.routers.*`
- `sqlalchemy`, `asyncpg`, `redis`

## Getting Started

1. Copy this directory to `app/modules/external/<your_vendor>/<your_module>/`
2. Edit `semptify.module.json` with your module's details
3. Implement your router in `router.py`
4. Compute content hash: `python -m app.core.external_loader hash <module_dir>`
5. Update `content_hash` in manifest
6. Submit via `/dev/external/submit` (when available) or contact admin

## Lifecycle

1. **Submitted** — Developer submits module
2. **Reviewed** — Admin reviews manifest, permissions, code
3. **Sandboxed** — Module runs in `dev_only` mode, admin only
4. **Tested** — Admin runs module's test suite, verifies permissions
5. **Approved** — Module promoted to `experimental`, visible to admin + opt-in users
6. **Beta** — Module promoted to `beta`, visible to users with `beta_dashboard` flag
7. **Stable** — Module promoted to `stable`, visible to all applicable roles
8. **Revoked** — Admin can revoke at any time

## Permissions Reference

| Permission | Description |
|------------|-------------|
| `vault.read` | Read user's vault files |
| `vault.write` | Upload/modify vault files |
| `timeline.read` | Read timeline events |
| `timeline.write` | Create timeline events |
| `overlay.read` | Read overlays |
| `overlay.write` | Create/modify overlays |
| `document.read` | Read document content |
| `document.write` | Upload/modify documents |
| `notification.send` | Send notifications to user |
| `user.profile.read` | Read user profile (name, role) |
| `user.contacts.read` | Read user's contacts |

## License

This template is MIT licensed. Replace with your module's license.
