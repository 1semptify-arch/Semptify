# Blueprint — Universal "Media Player" viewer + docx edit (liquid, resizable)

**Date:** 2026-09-21 | **Status:** approved by Brad 2026-09-21 (expanded scope) | **Task:** `docx-preview-edit-2026-09-21`

## Problem it solves

Today a user uploads a document and sees only its **filename** before it goes to
the vault. For `.docx` files it is worse: browsers cannot render docx, so Document
Center's viewer (`showIframeViewer` / `previewLocalFile`) silently falls through to
an iframe that downloads or shows nothing. Tenants, advocates, legal, and managers
cannot verify "is this the right file?" — the exact check Brad asked for.

Brad's direction (2026-09-21): **accumulate all formats into one reusable viewer —
a "media player" in the UI** — borderless, resizable, liquid layout, not a
docx-only one-off.

## Type

Feature slice on an **existing** module (`document_center`, CORE tier, stable) plus
one standalone master-repo tool. Not a new registered module — no `product_manifest.py`
change, no capability change, no new tier.

## Scope — what it does

1. **One shared component — `media_player.js` + `media-player.css`.**
   A single `SemptifyMediaPlayer` component that takes a `File`/`Blob`/URL +
   filename/mime and renders the right surface, in order:
   - `.docx` → HTML via vendored **mammoth.browser.js** (BSD-2-Clause), fully
     client-side — bytes never leave the device for preview.
   - `.pdf` → native `<iframe>`/pdf.js path (existing behavior preserved).
   - images → `<img>` (keeps the `.dc-image-overlay` wrapper for Pass 0 regions).
   - `.txt`/`.md`/`.csv`/`.log`/`.html` → text render (`FileReader`, escaped).
   - audio/video (`mp3`/`m4a`/`wav`/`ogg`/`mp4`/`webm`/`mov`) → native
     `<audio>`/`<video>` controls — covers voice-memo/quick-capture files.
   - `.doc` (legacy binary) and unknown types → honest "this file type can't be
     previewed — check the filename carefully" note, never a fake render.
   Presentation: **no card borders** (zone-background separation per the design
   rules), **liquid sizing** (fluid, fills its host), **user-resizable**
   (`resize: both` + sensible min clamps) — works inside the upload modal, the DC
   viewer surface, and the standalone tool.
2. **Pre-upload preview (the core ask).** After a file is picked in the DC upload
   modal — *before* Upload is pressed — the media player renders the file's real
   content inside the modal so the user verifies it, not just the name.
3. **Vaulted docx viewing.** `selectDoc` detects `.docx`, fetches the existing
   `/api/dc/document/{id}/view` bytes as `arrayBuffer`, renders via the media
   player into the viewer surface instead of the dead iframe path.
4. **Light edit.** "Edit" toggle on a rendered docx → `contenteditable` →
   "Download .docx" via vendored **html-docx-js** (MIT), and "Save copy to vault"
   which posts the edited file through the existing `/api/intake/upload/auto`
   (creates a *new* document record named `…-edited.docx`, clearly labeled as a copy).
5. **Standalone tool** `C:\master-repo\tools\docx-studio\index.html` — zero-server
   page (open in any browser): pick a file → media-player preview → edit →
   save .docx. Same vendored libs, self-contained copy under
   `tools/docx-studio/vendor/`.

## Scope — what it explicitly does NOT do

- No `.doc` (binary) parsing — fallback message only.
- **No in-place vault overwrite.** Editing saves a *copy*; replacing the original
  vault document needs a versioning decision (separate task).
- No new DB tables. No new API endpoints in v1.
- No server-side docx rendering — preview stays client-side (privacy + speed).
- No OCR/pipeline changes. Intake confirm loop untouched.
- `app/modules/onboarding/` — not touched (NO-TOUCH).

## Roles

Everyone who can open Document Center (tenant, advocate, manager, legal — the
module is already in their capability defaults). Nothing new to grant.

## New DB tables

None.

## New endpoints

None in v1 (reuses `/api/dc/document/{id}/view` and `/api/intake/upload/auto`).

## Existing modules/services called

- `document_center` viewer + upload modal (`static/js/document_center.js`,
  `app/templates/pages/document_center.html`, `static/css/document-center.css`).
- `intake` upload endpoint (`/api/intake/upload/auto`) for "save copy to vault".

## Files touched

- `static/js/vendor/mammoth.browser.min.js` *(new, vendored)*
- `static/js/vendor/html-docx.min.js` *(new, vendored — self-contained bundle incl. jszip)*
- `static/js/media_player.js` *(new — the shared viewer/edit component)*
- `static/css/media-player.css` *(new — tokens only, borderless, liquid, resizable)*
- `static/js/document_center.js` — wire upload preview + docx viewing + edit
- `app/templates/pages/document_center.html` — css/script tags, preview pane, edit buttons
- `tools/docx-studio/` *(master-repo, new self-contained page + vendored copies)*

## Capability tier

CORE (rides inside document_center; no manifest change).

## Risk

Low — additive JS/CSS/template only; no Python changes; no pipeline changes.
Failure mode degrades to today's behavior (iframe fallback), never a dead end:
unpreviewable types get a plain-language note, upload still works.

## Copy rules

Plain language, no banned words ("free", "account", "log in"). Error states route
to "upload anyway" + help, never strand the user.

## Verification

- `python -m py_compile` N/A (no Python changed) — JS checked via `node --check`.
- Jinja template compiles.
- Live app on :8001: pick a real .docx → content visible pre-upload; vaulted docx
  renders in viewer; edit → download produces a valid .docx; 375px + 1280px passes;
  console clean.
- `python tests/test_ssot_architecture.py` unchanged (no navigation changes).
