---
mode: agent
description: Semptify Forge — canonical module development system. Use when building, testing, or promoting modules through the lifecycle pipeline.
---

<!-- Mirrors .devin/skills/forge/SKILL.md — keep both in sync when editing. -->

# Semptify Forge — Canonical Dev System

The Forge is the canonical module development system for Semptify. All new modules
must be built in the Forge (starting at `dev_only`) and progress through the
lifecycle pipeline before reaching production users.

## Access

- **URL:** `/admin/forge.html` (alias: `/admin/dev-lab.html`)
- **Access:** Admin role only (stealth admin guard)
- **Dashboard link:** ⚒️ Semptify Forge

## Lifecycle Pipeline

```
dev_only → preview → experimental → beta → stable
```

- **dev_only** — Admin-visible only. New modules start here.
- **preview** — Admin + selected testers. Feature flag controlled.
- **experimental** — Opt-in users. May have rough edges.
- **beta** — Production users, but clearly marked as beta.
- **stable** — Full production. All users see it.

**Deprecated** is a terminal state for modules being phased out (e.g., Judge module).

## Building a New Module

1. **Register the module** in `app/core/product_manifest.py`:
   ```python
   _register("app.modules.<name>.router", tags=("<Name>",), tier=ProductTier.DEV,
             lifecycle="dev_only", requires_role=("admin",),
             dev_notes="What this module does.",
             log_message="<Name> router connected")
   ```

2. **Create the module** at `app/modules/<name>/`:
   - `__init__.py` — exports `router`
   - `router.py` — FastAPI APIRouter with endpoints
   - `register.py` — ModuleEntry declaration
   - `tests/` — pytest test suite (required for promotion)

3. **Register contracts** in `register.py` for SSOT compliance:
   ```python
   from app.core.module_contracts import FunctionGroupContract, register_function_group
   register_function_group(FunctionGroupContract(...))
   ```

4. **Verify** it appears in the Forge at `/admin/forge.html` under "Forge Modules".

5. **Test** by clicking "Run Tests" in the module's Forge modal.

6. **Promote** when ready via the Forge UI "Promote" button. Promotion:
   - Sets a runtime override in PostgreSQL (`module_overrides` table)
   - Invalidates the module resolver cache
   - Takes effect immediately

## Forge Components

| Component | File | Purpose |
|---|---|---|
| Manifest | `app/core/product_manifest.py` | Module declarations |
| Resolver | `app/core/module_resolver.py` | Resolves which modules each user sees |
| Overrides | `app/core/module_overrides.py` | Admin runtime overrides (PostgreSQL) |
| Gate | `app/core/module_gate.py` | Gate enforcement |
| External Loader | `app/core/external_loader.py` | External module loading |
| Forge UI | `static/admin/dev_lab.html` | Admin UI (rebranded as Forge) |
| Forge Router | `app/modules/dev_lab/router.py` | API endpoints for Forge |
| Maturity | `app/modules/dev_lab/maturity.py` | Lifecycle checklists |
| Ideas | `app/modules/dev_lab/ideas.py` | Idea intake & promotion |

## Forge API Endpoints

- `GET /dev/lab` — List all dev_only/preview/experimental modules
- `GET /dev/lab/{module_path}` — Get module details
- `GET /dev/lab/{module_path}/status` — Maturity checklist status
- `POST /dev/lab/{module_path}/promote` — Promote to next lifecycle
- `POST /dev/lab/{module_path}/test` — Run module's test suite
- `GET /dev/lab/ideas` — List submitted ideas
- `POST /dev/lab/ideas` — Submit a new idea
- `POST /dev/lab/ideas/{idea_id}/promote` — Promote idea to module

## Rules

1. **All new modules start at `dev_only`** — no exceptions.
2. **Tests required for promotion** — the Forge checks for a `tests/` directory.
3. **Promotions persist in PostgreSQL** — survive restarts.
4. **Only admins see Forge modules** — production users see `stable` and `beta` only.
5. **Register contracts** — every new module must register FunctionGroupContracts.
6. **Use the Forge UI** — don't manually edit `module_overrides` table.
