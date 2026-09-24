---
description: Semptify Forge canonical module development system
---

# Semptify Forge

The Dev Lab has been rebranded as **Semptify Forge** — the canonical module development system.

- Canonical URL: `/admin/forge.html`
- Alias: `/admin/dev-lab.html`
- Access: dormant in this repo — no admin role exists (tenant-only, PR #317). Reachable only via Brad's env-credentialed ops elevation.
- Lifecycle pipeline: `dev_only` → `preview` → `experimental` → `beta` → `stable`.
- Ops promotes/demotes modules via runtime overrides.

## Workflow

The full Forge workflow is in `.devin/workflows/forge.md` (mirrored as `.github/prompts/forge.prompt.md`).

## Key components

- `app/core/product_manifest.py` — module declarations.
- `app/core/module_resolver.py` — resolves which modules each user sees.
- `app/core/module_overrides.py` — admin runtime overrides.
- `app/core/module_gate.py` — gate enforcement.
- `app/core/external_loader.py` — external module loading.
- `app/modules/dev_lab/` — Forge API, maturity checklists, idea intake.

## Rules

- Every new module starts at `dev_only`.
- Only ops-elevated sessions see `dev_only`/`preview` modules.
- Production users see `stable`/`beta` only.
