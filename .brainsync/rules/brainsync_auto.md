

# Project Memory — Semptify5.0
> 479 notes | Score threshold: >40

## Safety — Never Run Destructive Commands

> Dangerous commands are actively monitored.
> Critical/high risk commands trigger error notifications in real-time.

- **NEVER** run `rm -rf`, `del /s`, `rmdir`, `format`, or any command that deletes files/directories without EXPLICIT user approval.
- **NEVER** run `DROP TABLE`, `DELETE FROM`, `TRUNCATE`, or any destructive database operation.
- **NEVER** run `git push --force`, `git reset --hard`, or any command that rewrites history.
- **NEVER** run `npm publish`, `docker rm`, `terraform destroy`, or any irreversible deployment/infrastructure command.
- **NEVER** pipe remote scripts to shell (`curl | bash`, `wget | sh`).
- **ALWAYS** ask the user before running commands that modify system state, install packages, or make network requests.
- When in doubt, **show the command first** and wait for approval.

**Stack:** Python · FastAPI · DB: PostgreSQL, Redis, SQLAlchemy

## 📝 NOTE: 1 uncommitted file(s) in working tree.\n\n## Important Warnings

- **⚠️ GOTCHA: Added session cookies authentication** — - - what-changed in shared-context.json — confirmed 3x
+ - Added sessi
- **⚠️ GOTCHA: Added session cookies authentication** — - - ⚠️ GOTCHA: Patched security issue Patched
+ - gotcha in shared-con
- **gotcha in shared-context.json** — -     }
+     },
-   ]
+     {
- }
+       "id": "fbaa2c3cb5a3c0ae",
+
- **⚠️ GOTCHA: Patched security issue Patched** — - - problem-fix in agent-rules.md
+ - Patched security issue Check — p
- **⚠️ GOTCHA: Added session cookies authentication — evolves the database schema to support...** — - > 294 notes | Score threshold: >40
+ > 295 notes | Score threshold: 

## Project Standards

- Added session cookies authentication — confirmed 3x
- Added session cookies authentication — confirmed 3x
- Added JWT tokens authentication — confirmed 5x
- Added session cookies authentication — confirmed 5x
- what-changed in shared-context.json — confirmed 3x
- Patched security issue RedirectResponse — protects against XSS and CSRF token... — confirmed 6x
- what-changed in brainsync_auto.md — confirmed 3x
- Added session cookies authentication — confirmed 3x

## Known Fixes

- ❌ File updated (external): server_error.log → ✅ problem-fix in server_error.log
- ❌ - from fastapi import FastAPI, Request, HTTPException → ✅ Patched security issue Python — hardens HTTP security headers
- ❌ - - problem-fix in server_error.log → ✅ problem-fix in agent-rules.md
- ❌ File updated (external): .mypy_cache/3.11/app/core/errors.meta.json → ✅ problem-fix in errors.data.json
- ❌ - - problem-fix in error.html → ✅ problem-fix in agent-rules.md

## Recent Decisions

- decision in services.meta.json
- decision in cards.css
- decision in timeout.meta.json
- decision in seed_court_data.meta.json

## Learned Patterns

- Always: what-changed in brainsync_auto.md — confirmed 3x (seen 2x)
- Always: what-changed in brainsync_auto.md — confirmed 3x (seen 3x)
- Always: what-changed in brainsync_auto.md — confirmed 3x (seen 4x)
- Agent generates new migration for every change (squash related changes)
- Agent installs packages without checking if already installed

### 📚 Core Framework Rules: [tinybirdco/tinybird-python-sdk-guidelines]
# Tinybird Python SDK Guidelines

Guidance for using the `tinybird-sdk` package to define Tinybird resources in Python.

## When to Apply

- Installing or configuring tinybird-sdk
- Defining datasources, pipes, or endpoints in Python
- Creating Tinybird clients in Python
- Using data ingestion or queries in Python
- Running tinybird dev/build/deploy commands for Python projects
- Migrating from legacy .datasource/.pipe files to Python
- Defining connections (Kafka, S3, GCS)
- Creating materialized views, copy pipes, or sink pipes

## Rule Files

- `rules/getting-started.md`
- `rules/configuration.md`
- `rules/defining-datasources.md`
- `rules/defining-endpoints.md`
- `rules/client.md`
- `rules/low-level-api.md`
- `rules/cli-commands.md`
- `rules/connections.md`
- `rules/materialized-views.md`
- `rules/copy-sink-pipes.md`
- `rules/tokens.md`

## Quick Reference

- Install: `pip install tinybird-sdk`
- Initialize: `tinybird init`
- Dev mode: `tinybird dev` (uses configured `dev_mode`, typically branch)
- Build: `tinybird build` (builds against configured dev target)
- Deploy: `tinybird deploy` (deploys to main/production)
- Preview in CI: `tinybird preview`
- Migrate: `tinybird migrate` (convert .datasource/.pipe files to Python)
- Server-side only; never expose tokens in browsers


### 📚 Core Framework Rules: [czlonkowski/n8n-code-python]
# Python Code Node (Beta)

Expert guidance for writing Python code in n8n Code nodes.

---

## ⚠️ Important: JavaScript First

**Recommendation**: Use **JavaScript for 95% of use cases**. Only use Python when:
- You need specific Python standard library functions
- You're significantly more comfortable with Python syntax
- You're doing data transformations better suited to Python

**Why JavaScript is preferred:**
- Full n8n helper functions ($helpers.httpRequest, etc.)
- Luxon DateTime library for advanced date/time operations
- No external library limitations
- Better n8n documentation and community support

---

## Quick Start



### Essential Rules

1. **Consider JavaScript first** - Use Python only when necessary
2. **Access data**: `_input.all()`, `_input.first()`, or `_input.item`
3. **CRITICAL**: Must return `[{"json": {...}}]` format
4. **CRITICAL**: Webhook data is under `_json["body"]` (not `_json` directly)
5. **CRITICAL LIMITATION**: **No external libraries** (no requests, pandas, numpy)
6. **Standard library only**: json, datetime, re, base64, hashlib, urllib.parse, math, random, statistics

---

## Mode Selection Guide

Same as JavaScript - choose based on your use case:

### Run Once for All Items (Recommended - Default)

**Use this mode for:** 95% of use cases

- **How it works**: Code executes **once** regardless of input count
- **Data access**: `_input.all()` or `_items` array (Native mode)
- **Best for**: Aggregation, filtering, batch processing, transformations
- **Performance**: Faster for multiple items (single execution)



### Run Once for Each Item

**Use this mode for:** Specialized cases only

- **How it works**: Code executes **separately** for each input item
- **Data access**: `_input.item` or `_item` (Native mode)
- **Best for**: Item-specific logic, independent operations, per-item validation
- **Performance**: Slower for large datasets (multiple executions)



---

## Python Modes: Beta vs Native

n8n offers two Python execution modes:

### Python (Beta) - Recommended
- **Use**: `_input`, `_json`, `_node` helper syntax
- **Best for**: Most Python use cases
- **Helpers available**: `_now`, `_today`, `_jmespath()`
- **Import**: `from datetime import datetime`



### Python (Native) (Beta)
- **Use**: `_items`, `_item` variables only
- **No helpers**: No `_input`, `_now`, etc.
- **More limited**: Standard Python only
- **Use when**: Need pure Python without n8n helpers



**Recommendation**: Use **Python (Beta)** for better n8...
(truncated)

- [Python] Use type hints for function arguments and return types
- [Python] Don't use mutable default arguments (def f(items=[]) is a bug)

## Available Tools (ON-DEMAND only)
- `sys_core_01(q)` — Deep search when stuck
- `sys_core_05(query)` — Full-text lookup
> Context above IS your context. Do NOT call sys_core_14() at startup.
