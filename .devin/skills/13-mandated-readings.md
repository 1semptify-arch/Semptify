---
description: Mandatory pre-flight reading checklist
---

# Mandated Reading Checklist

Before starting any coding session, read these files in this order:

1. `BUILD_STATE.md` — last shipped, known broken, pending.
2. `ACTIVE_CONTEXT.md` — current priority.
3. `PROJECT_BIBLE.md` — canonical hierarchy and gates.
4. `BUILD_GUIDE_SSOT.md` — active features and known issues.
5. `GOVERNING_SYSTEM_SSOT.md` — routing and cookie rules.
6. `AGENTS.md` — AI behavior and Known Failure Registry.

Then verify:

- Python 3.11.9 only; use `venv311`.
- NEVER use `datetime.now()`; use `utc_now()` from `app.core.utc`.
- NEVER use bare `except:`; use specific exception types.
- NEVER create `_v2`, `_new`, or `_fixed` files; use the swap protocol.
- NEVER hardcode URL strings; use `navigation.get_stage()`.
- NEVER run `git clean -fd` or `git reset --hard` without checking `git log`.
- Imports always at the top of the file; never mid-file injection.
- No local file storage for user data; user data lives in the user's cloud.

Also see `.devin/workflows/preflight.md` and `.github/prompts/preflight.prompt.md`.
