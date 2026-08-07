# compile_ai_context.py — Manual

Bundles Semptify's canonical project docs into one paste-ready `AI_HANDOFF_PACKET.md` so you can sync context into Gemini, MSN Copilot, or a fresh Windsurf session without re-gathering files by hand.

## Location

- Script: `scripts/compile_ai_context.py`
- Output: `AI_HANDOFF_PACKET.md` (written to the **project root**, not `scripts/`)
- Run from: **repo root** (`C:\Semptify\Semptify-FastAPI`)

Paths inside the script are relative to the repo root. Running it from anywhere else will silently skip every file.

## When to run

- Starting a fresh AI session with no prior context
- Switching between AI tools (Gemini / Copilot / Windsurf)
- Before a `/preflight` or handoff
- After significant changes to any listed canonical doc
- Any time you want the AI to stop guessing file names

## How to run

```powershell
# From the repo root — NOT from inside scripts/
cd C:\Semptify\Semptify-FastAPI
python scripts/compile_ai_context.py
```

You should see one line per target doc:

```
  merged: Semptify_AI_Orchestration_Blueprint.md
  SKIPPED (not found): <path>
  merged: .devin/workflows/preflight.md
  ...
Done. Packet written to: AI_HANDOFF_PACKET.md
```

## Output

`AI_HANDOFF_PACKET.md` contains:

1. Header with generation timestamp + current git commit hash
2. Reference note about `Semptify_Master_Inventory_LIVE.xlsx` (not inlined — it's a spreadsheet)
3. One `## SOURCE FILE: <path>` section per target doc, with the full file contents inlined
4. A placeholder line for any file that was not found at the expected path

Copy the entire file contents into the AI's first message.

## Target docs (the canonical list)

Defined in `TARGET_DOCS` near the top of the script. Current list:

| Path | Status |
|------|--------|
| `Semptify_AI_Orchestration_Blueprint.md` | merged |
| `docs/admin/Semptify_Site_GUI_Framework.md` | **needs path fix** — actually lives at `DOCUMENTS/Semptify_Site_GUI_Framework.md` |
| `.devin/workflows/preflight.md` | merged |
| `ACTIVE_CONTEXT.md` | merged |
| `BUILD_STATE.md` | merged |

## When a file is skipped

The script does NOT fail on a missing file — it writes a `*(File not found at this path — skipped.)*` placeholder and continues. This is intentional so a stale path never blocks packet generation, but it means **you must read the console output** to know which files actually got inlined.

If you see `SKIPPED (not found):` for a file you know exists:

1. Find its real location: `find . -name "<filename>"` (or use the IDE file search)
2. Update the path in `TARGET_DOCS` inside `scripts/compile_ai_context.py`
3. Re-run the script
4. Confirm the console now says `merged:` for that file

## Adding a new doc to the packet

Edit `TARGET_DOCS` in `scripts/compile_ai_context.py`:

```python
TARGET_DOCS = [
    "Semptify_AI_Orchestration_Blueprint.md",
    "DOCUMENTS/Semptify_Site_GUI_Framework.md",   # fixed path
    ".devin/workflows/preflight.md",
    "ACTIVE_CONTEXT.md",
    "BUILD_STATE.md",
    "PROJECT_BIBLE.md",                            # new entry
]
```

Rules for the list:

- Paths are relative to the repo root
- Text files only (`.md`, `.txt`, `.py`, etc.) — the script inlines raw contents
- For non-text files (xlsx, pdf, images), do NOT add them to `TARGET_DOCS` — instead add a note to `WORKBOOK_NOTE` so the AI knows they exist
- Keep the list short — only true canonical docs. Bigger packets cost more tokens and dilute signal

## What NOT to do

- **Do not** run the script from inside `scripts/` — paths are repo-root-relative
- **Do not** add binary files (xlsx, pdf, png) to `TARGET_DOCS` — they will inline as garbage
- **Do not** edit `AI_HANDOFF_PACKET.md` by hand — it is generated output. Edit the source docs and re-run
- **Do not** commit `AI_HANDOFF_PACKET.md` to git — it is a transient handoff artifact, not a source doc. (If you want to track it, add to `.gitignore`.)
- **Do not** add a file to `TARGET_DOCS` unless it is truly canonical — stale entries silently degrade every packet

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Every file shows `SKIPPED` | Ran from wrong directory | `cd` to repo root, re-run |
| One file shows `SKIPPED` but it exists | Path in `TARGET_DOCS` is stale | Find real path, update `TARGET_DOCS`, re-run |
| `DeprecationWarning: datetime.utcnow()` | Python 3.11+ warns on this | Cosmetic only — does not affect output. If it bothers you, replace with `datetime.now(datetime.UTC)` |
| `NO_GIT_REPOSITORY_DETECTED` in header | Not in a git repo, or git not on PATH | Run from inside the repo, or ignore — packet still generates |
| Packet is huge | Too many docs in `TARGET_DOCS` | Trim the list to true canonicals only |
| Packet is stale | Source doc changed but script not re-run | Re-run the script before each handoff |

## Verification checklist

After running:

- [ ] Console shows `merged:` for every expected file
- [ ] No `SKIPPED` lines for files that should exist
- [ ] `AI_HANDOFF_PACKET.md` exists in repo root
- [ ] Header shows the current git commit hash (not `NO_GIT_REPOSITORY_DETECTED`)
- [ ] Timestamp in header matches when you ran it

## Related files

- `scripts/compile_ai_context.py` — the script this manual describes
- `AI_HANDOFF_PACKET.md` — generated output (transient, not a source doc)
- `Semptify_Master_Inventory_LIVE.xlsx` — referenced by `WORKBOOK_NOTE`, not inlined
- `AGENTS.md` — the mandatory-reading list this packet helps satisfy
