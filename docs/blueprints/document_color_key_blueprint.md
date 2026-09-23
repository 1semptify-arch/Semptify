# Document Color Key Blueprint — highlighted text + legend page

**Status:** IMPLEMENTED (v1) — built and verified 2026-09-23; see task `document-color-key-2026-09-23`
**Module path:** extends `document_center` viewer (`static/js/media_player.js`) + overlay machinery; companion to `advocate_collaboration_pipeline_blueprint.md`
**Type:** Feature slice on existing modules
**Pillar:** KNOW (crosses RECORD for authoring)
**Tier:** CORE candidate — DEV first
**Date:** 2026-09-23

## Problem

Documents get highlighted and annotated (HIGHLIGHT / FOOTNOTE / NOTE /
TRACKED_EDIT overlays already exist), but there is no way to see *what the
colors mean* or *where all the highlights are*. Brad's spec (2026-09-23):
"the document viewer should have everything highlighted to the notes and
Semptify footnotes, with a per-document color key — one page that defines the
colored highlighted text and links to the text indicated."

Two gaps:

1. **No legend.** Colors carry no declared meaning; a reader can't tell
   "yellow = harassment evidence" from "yellow = I liked this part."
2. **No index.** Highlights live in-place only — no page lists every
   highlighted passage by color with links into the document.

## What already exists (reuse)

- `media_player.js` / `media-player.css` — universal viewer surface (docx via
  mammoth, pdf, images, text), built and wired into Document Center.
- Overlay types: `HIGHLIGHT` (`{range, color, note?}`), `FOOTNOTE`
  (`{number, range, content, citation?}`), `NOTE`, `TRACKED_EDIT` — storage,
  create/list/delete all live (`advocate/router.py`, unified overlay manager).
- Overlay payloads are free-form JSON — a `color_key` payload or document-level
  KEY overlay fits the existing model without schema surgery.

## Scope — what it does

1. **Per-document Color Key.** Each document gets an optional legend:
   color swatch → plain-English meaning, defined by the tenant (e.g.
   yellow = harassment evidence, red = contradiction, blue = deadline/date,
   green = money/payment). Stored as a `DOCUMENT_KEY` overlay anchored to the
   document so it travels with it.
2. **Legend page/panel.** One view per document showing every defined color,
   and under each color every highlighted passage — quoted text, page/section,
   linked footnotes — each entry clicking through to scroll-highlight the
   passage in the viewer. Chronological/document order per the GUI rule.
3. **Viewer rendering.** Highlights painted onto the media-player surface
   (text formats first: docx-rendered HTML and txt/md are the tractable
   surfaces; PDF highlight painting over iframe/pdf.js is a harder slice —
   parked unless simple). Footnote markers render as superscript numbers
   linking to footnote text at the bottom of the view.
4. **Tenant self-annotation.** Today `annotate_document` is advocate-only
   (`_require_advocate`). Add a tenant path so a tenant can mark up their
   *own* documents — required for Brad's use and for the feature to matter
   outside the advocate flow.
5. **Co-view tie-in (future slice, not v1).** During a live co-view session the
   color key is the shared vocabulary — "the red parts" means something to
   both parties.

## Does NOT (v1)

- No OCR-region highlighting on scanned images (Pass 0 regions are a separate
  system — read-only display is OK, drawing boxes is not v1).
- No shared/global legend templates — key is per-document (a "copy key from
  another doc" convenience is a later nicety).
- No advocate-side changes — existing advocate annotations simply appear in
  the key alongside tenant ones, labeled by author.
- No changes to onboarding.

## Open questions for Brad

- [ ] Fixed palette (6–8 named colors) or free color choice? Fixed palette is
      simpler and keeps keys readable.
- [ ] Legend as its own page (`/document/{id}/key`) or a side panel in the
      viewer? Page favors the print/share use-case; panel favors live reading.
- [ ] Should a color key auto-appear in packet exports? (An exported PDF with
      a legend page + numbered highlights is a genuinely strong attorney
      artifact — but adds export work.)
- [ ] Who defines the key on shared docs — tenant only, or can the advocate
      propose colors for tenant approval?

## Build order

1. `DOCUMENT_KEY` overlay + per-doc legend storage
2. Legend page listing colors → passages → links (the core ask)
3. Highlight/footnote painting in media_player (text surfaces first)
4. Tenant self-annotate endpoint + viewer controls
5. (later) PDF painting, packet-export legend page, co-view integration
