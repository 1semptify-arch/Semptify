# HANDOFF: Feature-Flag System Unification

**Date:** 2026-08-25  
**Agent:** SWE-1.7-Max  
**Purpose:** Investigate why Semptify has two feature-flag systems, what each one does, where they diverge, and what unification would involve. This is a read-only investigation; no code was changed.

---

## Bottom line up front

Semptify currently has **two independent feature-flag systems with no shared state**:

- `app/core/feature_flags.py` — a small in-memory store that backs `FeatureFlagMiddleware` and the `/admin/api/flags` endpoints in `app/main.py`.
- `app/core/features.py` — a DB-backed `FeatureFlagManager` used by `role_ui`, `admin_console`, `module_resolver`, and the startup `ensure_schema()`.

The in-memory system is **not persisted**: toggling a flag in `/admin/api/flags` only lasts until the process restarts and has no effect on the DB-backed checks used by the rest of the app. The DB-backed system is the one with persistence, schema support, env overrides, role/rollout gating, and existing tests.

The `feature_flags` database table is **not missing**. It exists with expected rows in `semptifty_db`, `neondb`, and local SQLite; `app/core/features.py:ensure_schema()` creates it at startup. The `ACTIVE_CONTEXT.md` note that listed it as missing has been corrected.

Unification is feasible and likely low-to-medium effort, but it is a design decision, not a simple bug fix. The main open question is whether the route-kill-switch concept (used by the middleware) should be absorbed into the `Feature` enum or kept as a separate, thinner gate.

---

## 1. What each system does

### 1.1 In-memory system: `app/core/feature_flags.py`

- **Location:** `app/core/feature_flags.py`.
- **State:** a process-local `dict` named `_flags`, hardcoded at module load time.
- **Hardcoded defaults (all `True`):**
  - `admin_access`
  - `copilot`
  - `voice_to_text`
  - `communication_import`
  - `resource_directory`
- **Route map:** `ROUTE_FLAG_MAP` maps URL prefixes to one of those five names:

  | Prefix | Flag |
  |---|---|
  | `/admin` | `admin_access` |
  | `/api/copilot`, `/tenant/copilot` | `copilot` |
  | `/api/voice` | `voice_to_text` |
  | `/api/import` | `communication_import` |
  | `/api/resources`, `/tenant/resources` | `resource_directory` |

- **Consumers:**
  - `FeatureFlagMiddleware` (`app/main.py:1870`) — checks every request against `ROUTE_FLAG_MAP` and returns HTTP 503 if the matching flag is `False`.
  - `/admin/api/flags` (GET, PUT, POST toggle) in `app/main.py:2823-2849` — reads/writes the in-memory store only.
- **Characteristics:** no persistence, no cache TTL, no role/rollout support, no tests.

### 1.2 DB-backed system: `app/core/features.py`

- **Location:** `app/core/features.py`.
- **State:** a PostgreSQL/SQLite `feature_flags` table, plus a 60-second in-memory cache in `FeatureFlagManager`.
- **Key features:**
  - `Feature` `StrEnum` with 23 product-level flags (`ai_copilot`, `eviction_defense`, `premium_export`, etc.).
  - `DEFAULT_ENABLED` code defaults.
  - Env overrides (`FEATURE_<NAME>=true/false`) take priority.
  - DB row is the next source of truth.
  - Supports `rollout_percent` and `allowed_roles`.
  - `set_enabled()` persists with `ON CONFLICT` upsert.
  - `ensure_schema()` creates the table (and seeds 5 legacy rows) at startup so local SQLite gets the same table as PostgreSQL.
- **Consumers:**
  - `app/main.py` lifespan (`ensure_feature_flags_schema` at line 538) — creates/maintains the table.
  - `app/modules/role_ui/router.py` (`get_role_ui`) — overlays DB feature flags onto role-specific UI state.
  - `app/modules/admin_console/router.py` (`/api/system/feature-flags` GET/POST) — reads/writes the DB-backed store.
  - `app/core/module_resolver.py` — checks `entry.feature_flag` against `Feature` to decide if a module is enabled.
  - `tests/test_features.py` — 19 tests covering the manager, decorators, env overrides, and role/rollout logic.

---

## 2. Current state of the database table

The table exists in all currently relevant environments:

- `semptifty_db` (Render/Neon) — 28 rows, including the 5 legacy rows and all 23 `Feature` enum values.
- `neondb` (Neon) — table exists.
- Local SQLite — table exists and is created by `ensure_schema()` at startup.

The earlier "missing table" warning appears to have been resolved by the `ensure_schema()` startup path and the existing Alembic migration `20260609_add_feature_flags_table.py`. `ACTIVE_CONTEXT.md` has been updated to remove the stale blocker.

---

## 3. Where the two systems diverge

### 3.1 Namespace / shape mismatch

The two systems use different sets of flag names:

| In-memory `feature_flags.py` | DB-backed `features.py` (`Feature` enum) |
|---|---|
| `admin_access` | no equivalent |
| `copilot` | `ai_copilot` (similar concept, different key) |
| `voice_to_text` | no equivalent |
| `communication_import` | no equivalent |
| `resource_directory` | no equivalent |

Only `copilot` ↔ `ai_copilot` is an obvious semantic overlap, and even that is keyed differently. A naive merge would either need new `Feature` entries for the route-gate concepts, or a separate route-gate layer on top of `FeatureFlagManager`.

### 3.2 Admin surface mismatch

There are two admin UIs for the same word "feature flag":

- `/admin/api/flags` in `main.py` → in-memory, ephemeral.
- `/admin/api/system/feature-flags` in `admin_console/router.py` → DB-backed, persistent.

Changing one does not change the other. There is also no UI path from the ephemeral endpoints to the persistent ones.

### 3.3 Runtime behavior mismatch

| Property | In-memory `feature_flags.py` | DB-backed `features.py` |
|---|---|---|
| Storage | process-local `dict` | PostgreSQL/SQLite table |
| Persistence | none (resets on restart) | persistent, with upsert |
| Default when unknown | `True` (fail-open) | `DEFAULT_ENABLED[...]` or `False` |
| Role/rollout | no | yes |
| Env override | no | yes |
| Cache | none (always instant) | 60-second in-memory cache |
| Tests | none | 19 tests |

### 3.4 Current values

As of this writing, the in-memory defaults are all `True`. The DB has the 5 legacy rows at their hardcoded defaults (`eviction_defense_nd` `true`, the rest `false`) plus the `Feature` enum values at their `DEFAULT_ENABLED` defaults. Because the in-memory system is ephemeral, there is no durable divergence yet — but the two systems are already pointing at different concepts.

---

## 4. Hot-path / performance considerations

### 4.1 Middleware is on every request

`FeatureFlagMiddleware` runs on the request path. It currently does a hash lookup and, at worst, a string-prefix scan of 7 `ROUTE_FLAG_MAP` entries. This is essentially free.

If the middleware were switched to `FeatureFlagManager.is_enabled()`:

- The first request after cache expiry would issue a single `SELECT ... FROM feature_flags` (already the existing `_refresh_from_db()` query).
- After that, every check is an in-memory dict lookup for 60 seconds.
- If the database is unreachable, `FeatureFlagManager` logs a warning and falls back to `DEFAULT_ENABLED` / cache. Middleware would need to decide whether to fail-open or 503 in that path.
- There is a small thundering-herd risk: multiple concurrent requests arriving right after cache expiry can all trigger `_refresh_from_db()` at once. The current code has no lock around the cache refresh. For a 60-second TTL this is unlikely to matter, but it is worth noting.

### 4.2 First request after deploy / cache expiry

Because `_refresh_from_db()` is async and `FeatureFlagMiddleware.dispatch()` is already async, the call pattern is straightforward. The DB query is small (≤30 rows). On the current Render/SQLite tiers this is negligible.

---

## 5. Full consumer inventory

### In-memory system consumers

1. `app/core/feature_flags.py:FeatureFlagMiddleware`
2. `app/main.py:1870` — adds `FeatureFlagMiddleware` to the app.
3. `app/main.py:2823-2849` — three `/admin/api/flags` endpoints.

No other imports of `app.core.feature_flags` were found in `app/` or `tests/`.

### DB-backed system consumers

1. `app/core/features.py` — the system itself.
2. `app/main.py:538` — `ensure_feature_flags_schema()` during lifespan.
3. `app/modules/role_ui/router.py` — overlays DB flags for role UI.
4. `app/modules/admin_console/router.py` — `/api/system/feature-flags` endpoints.
5. `app/core/module_resolver.py` — checks module lifecycle via `Feature`.
6. `tests/test_features.py` — the test suite.

---

## 6. Preliminary unification complexity (no decision)

### Option A: Move the middleware and ephemeral admin endpoints onto `FeatureFlagManager`

This would make `app/core/features.py` the single system.

**What would need to happen:**

1. Decide how to represent route-gate flags (`admin_access`, `copilot`/`ai_copilot`, `voice_to_text`, `communication_import`, `resource_directory`) in the DB table.
   - Sub-option A1: add new `Feature` enum members for the route-gate concepts.
   - Sub-option A2: keep a small route-prefix → `Feature` mapping and rely on `Feature.AI_COPILOT` for the copilot route, then add missing `Feature` members for the others.
2. Replace `FeatureFlagMiddleware` with a middleware that calls `await features.is_enabled(...)`.
   - Must choose fail-open vs. 503 when the DB query fails.
   - Must handle unknown route flags gracefully.
3. Remove or redirect the `/admin/api/flags` endpoints in `app/main.py` to the existing `/admin/api/system/feature-flags` endpoints in `admin_console`.
4. Add tests for the middleware and for the new `Feature` members, if any.
5. Delete `app/core/feature_flags.py`.

**Rough effort:** low-to-medium. The main work is naming/namespace mapping and choosing the fail-open behavior. The DB table and persistence layer already exist.

### Option B: Keep two layers, but make them consistent

Treat `feature_flags.py` as a lightweight **route kill-switch** layer and `features.py` as the **product feature** layer, but wire the kill-switch layer to read from `FeatureFlagManager`.

**What would need to happen:**

1. Keep `ROUTE_FLAG_MAP` but have it call `await features.is_enabled(...)` for each prefix.
2. Either add route-gate `Feature` members or keep a local mapping from route-gate names to existing `Feature` names.
3. Keep the `/admin/api/flags` endpoints, but make them write through `FeatureFlagManager.set_enabled()`.
4. Add tests for the middleware and admin endpoints.

**Rough effort:** low. It preserves the route-gate abstraction while eliminating the duplicate in-memory store.

### Option C: Do nothing

Leave both systems as-is and document which admin endpoints control which behavior.

**Rough effort:** zero, but the divergence will continue to surprise anyone toggling a feature flag.

---

## 7. Noticed but not changed

- `FeatureFlagManager.get_status()` hardcodes `"source": "postgresql"` even when running on SQLite.
- `FeatureFlagManager._refresh_from_db()` has no synchronization around cache refresh; concurrent requests after expiry can each hit the database.
- `tests/test_feature_flags.py` does not exist; the in-memory system has no test coverage.
- `Feature` enum includes premium/experimental names (`PREMIUM_EXPORT`, `PREMIUM_TEMPLATES`, `UNLIMITED_STORAGE`, `EXPERIMENTAL_AI_MODEL`, `EXPERIMENTAL_UI`) that may conflict with Semptify's non-commercial positioning. This is a product/copy question, not a technical one, and is out of scope here.

---

## 8. Key files referenced

- `app/core/feature_flags.py` — in-memory store and middleware.
- `app/core/features.py` — DB-backed `FeatureFlagManager`.
- `app/main.py` — middleware registration and ephemeral `/admin/api/flags` endpoints.
- `app/modules/admin_console/router.py` — DB-backed `/api/system/feature-flags` endpoints.
- `app/modules/role_ui/router.py` — role-gated DB feature flag consumer.
- `app/core/module_resolver.py` — module lifecycle feature-flag consumer.
- `tests/test_features.py` — test coverage for the DB-backed system.
- `ACTIVE_CONTEXT.md` — stale blocker note corrected in this session.
