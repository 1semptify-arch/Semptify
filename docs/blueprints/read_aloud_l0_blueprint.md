# Read Aloud L0 Blueprint

**Status:** DRAFT — pending approval
**Type:** Browser-native feature on public pages (one small JS include +
one control; no server, no new dependency)
**Pillar:** KNOW (access — reaches people who can't read the page)
**Tier:** L0 public
**Date:** 2026-11-06
**Toolbox entry:** `read_aloud` (planned, group=know, engine=page) —
"Have any page read to you instead of reading it."

## Problem

A tenant with low literacy, low vision, English as a second language, or
a cracked-screen phone has no way to *hear* a Semptify page today except
a full screen reader — which most people in this situation do not have
or do not know how to drive. The catalog `today` line says exactly that:
"Your device's built-in screen reader works on every Semptify page" —
true but thin.

The `backed_by` field lists `voice`, but **the voice module is
speech-to-text only** (`POST /transcribe`) — there is no TTS machinery
anywhere in the repo (verified: zero `speechSynthesis`/TTS references in
`app/` or `static/`). Server-side TTS would also be the wrong build:
audio generation costs compute, adds latency, and — worst — sends page
content context to a server pipeline for no benefit when every modern
browser already ships speech synthesis.

## Proposed shape

A **"Listen" control injected by one small vendored-own script** on
public pages, using the browser's built-in `speechSynthesis` API:

- One file `static/js/read-aloud.js` (~100 lines, no library — the Web
  Speech API is native). Loaded from `body/public_shell.html` so every
  public page gets it.
- One quiet button in the header/toolbar zone: "Listen to this page."
  States: play → pause/resume → stop. On unsupported browsers the button
  hides itself (`'speechSynthesis' in window` gate) — never a dead
  control.
- Reads the main content region (`<main>`/`page_body` block text),
  skipping nav/footer/CTAs. Uses the document's `lang` for voice
  selection, default rate, no highlight-follow in v1.
- **Nothing is sent to any server.** Speech is synthesized on the
  device — the strongest privacy posture and honest copy: "read aloud by
  your own device."
- Respects `prefers-reduced-motion` (no animated progress indicator),
  no autoplay, stops on navigation.

This is deliberately not the app-side "read-aloud" of the agent
companion (different surface, different audience) — this is for public
visitors only.

## Decision needed (Brad)

1. **Public pages only vs. tenant app pages too.** Recommended: public
   pages only in v1 — the tenant app pages carry personal content where a
   read-aloud button invites different expectations (and the vault-app
   audience already has the companion tooling). Adding it to
   `shell_base`/`gui` shells later is a one-line include if wanted.
2. **Scope of read region.** Recommended: main column only; sidebar
   ("Find local help" etc.) excluded — reading a sidebar mid-article is
   worse than not offering it. A per-template `data-read-aloud` region
   marker lets individual pages opt sections in/out later.
3. **Button placement.** Header zone next to the language selector if
   both exist — same "access" mental drawer. Not a floating widget
   (floating UI is the popup pattern we don't do).

## Scope if approved

- `static/js/read-aloud.js` (new, vendored-own code).
- `app/templates/body/public_shell.html` — script include + button
  markup in the header block.
- `toolbox.py` flip on the toolbox branch: `planned` → `live`,
  `today` → "Every public page can read itself aloud through your
  browser's built-in speech — the Listen button in the header."
  `backed_by` corrected (browser Web Speech API, not the `voice`
  module). **Blocked until the toolbox branch merges.**

## Verification

- `/credit-reports`, `/law-library`, `/help` at 375px and 1280px:
  button present, plays/pauses/stops, reads main content only.
- Unsupported-browser path: control absent, page unchanged.
- Console clean; no network requests triggered by playback (verify in
  network panel — the privacy claim must be mechanically true, not
  asserted).
- Voice sweep: control copy plain ("Listen to this page"), no hype.
