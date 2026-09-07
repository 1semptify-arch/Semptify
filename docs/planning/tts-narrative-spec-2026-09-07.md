# TTS Narrative System — Spec (Draft for Review)

**Task:** `semptify-nonai-narrative-vocal-output-2026-09-03`  
**Date:** 2026-09-07  
**Author:** Devin / SWE-1.7  
**Status:** Draft — pending Brad review

## 1. Goal

Add calm, user-controlled vocal narration to Semptify pages. The voice reads the **same authored text the user already sees on screen** — process narration, step labels, verified facts, and short explanations. It is **not** an AI that improvises, summarizes, or legal-advises. It is an accessibility and stress-reduction layer, not a new content source.

This pairs with the existing `voice_input.html` component, which already uses the browser's Web Speech API for speech-to-text.

## 2. Design Principles

1. **User-controlled, not auto-play.** No surprise audio. The user toggles TTS on per page and can pause/stop at any time.
2. **No new content generation.** TTS reads text that already exists in the rendered page: `process_indicator` narration, headings, verified facts, short guidance lines, CTA labels. No LLM, no summarization, no synthesized legal advice.
3. **Privacy-first.** V1 keeps all synthesis in the browser via `speechSynthesis`. No tenant document text or user input is sent to a cloud TTS service.
4. **Calm tone.** No urgency, no "alert" language. The same plain, nonprofit tenant-rights voice used in copy.
5. **Progressive Disclosure compatible.** TTS verbosity follows the same `intensity_level` dial as on-screen narration. First-time users hear more; returning users hear less.
6. **Cost-conscious.** V1 has no marginal cost. V2/V3 add optional cloud voices only for public, non-PII content and only if budget/quality justify it.

## 3. What It Reads — Surfaces

| Surface | What is read | Why |
|---|---|---|
| Public landing (`/`) | Hero h1, verified-fact claims + citations (read once each), footer trust line | Accessibility; users in crisis who cannot parse text |
| Portal / subject pages | Page title, short description, primary CTA | Wayfinding |
| In-task guide pages (`/gui/record/journal/create`, `/gui/know/law-library/get-statute`, `/gui/act/eviction-defense/calculate-deadlines`, etc.) | `process_indicator` step label and narration bullets as the state changes | Reduces anxiety during real waiting; keeps user oriented |
| `/tenant/get-help` | Narration block, questions, "Find my next step" result | Stressful triage moment |
| Document Center "What does this mean?" | Title, plain-English summary, one or two key action items (optional — see privacy note) | Complex document translated to speech |
| Law Library / state-law entries (future) | Short statute summary, deadline numbers, legal-aid link | Reading state-law fields aloud |

## 4. What It Does NOT Read

- User-typed answers or document uploads.
- Full document text from Document Center unless the user explicitly triggers it and the text is confirmed PII-free.
- Legal citations verbatim unless the user is on a "read source" screen.
- Anything marked `aria-hidden` or `data-tts-skip`.

## 5. V1 Architecture — Browser-Native (`speechSynthesis`)

### 5.1 Component

`static/js/tts_controller.js` — a new lightweight client module.

Responsibilities:
- Detect `window.speechSynthesis` support and the user's locale.
- Queue utterances from page elements marked `data-tts`.
- Honor a global `semptify_tts_enabled` localStorage toggle.
- Expose `play()`, `pause()`, `stop()`, `next()`, `previous()`.
- Read `data-tts-priority` to decide order (headings first, then narration, then detail).

### 5.2 Markup Contract

Templates add `data-tts` to elements they want vocalized:

```html
<h1 data-tts data-tts-priority="1">Document what happened. Know the verified facts.</h1>
<p data-tts data-tts-priority="2">When you click Find my next step, Semptify does the following:</p>
<ul data-tts data-tts-priority="2">
  <li>Reads your answers to understand the situation.</li>
  <li>Suggests the most useful next step.</li>
</ul>
```

`process_indicator` in `components/ui_composer.html` automatically wraps its narration in `data-tts` when TTS is enabled on the page.

### 5.3 UI Control

A small TTS widget is rendered in the site header next to the locale selector:

- **Speak icon** (▶) — start or resume reading the page.
- **Pause icon** (⏸) — pause.
- **Stop icon** (⏹) — stop and clear queue.
- The widget only appears on TTS-capable pages.
- It respects `prefers-reduced-motion` by defaulting to off and avoiding animated visual feedback.

### 5.4 Locale / Voice

- Use `document.documentElement.lang` or `getLocale()` (already in Jinja context).
- Select the first `speechSynthesis.getVoices()` voice matching the locale.
- Fallback to `en-US` default if no match.
- Rate: ~0.95, Pitch: 1.0 — calm defaults.

### 5.5 Sync With Page State

- On `process_indicator` state changes (`pending` → `running` → `complete`), the TTS controller cancels the current queue and re-reads the updated narration.
- It does not read intermediate async updates word-by-word; it re-reads the final visible text.
- For live regions, use `aria-live="polite"` and `data-tts-live` to trigger re-reading.

### 5.6 Intensity / Tapering

TTS verbosity is driven by the same `intensity_level` context passed to the template:

| `intensity_level` | Behavior |
|---|---|
| `High` | Read step label + full narration bullets. |
| `Standard` | Read step label + first narration bullet. |
| `Subtle` / `Off` | Read only the step label, or nothing. |

This is not a new server field. It reuses the `intensity_level` already available to `process_indicator` and the page context.

## 6. V2 — Cloud Voices for Public, Non-PII Content (Optional)

**Trigger:** Brad decides V1 browser voices are not clear/usable enough, and budget allows.

- Public landing and verified facts can be rendered to short MP3s server-side via a cloud TTS provider (e.g., Google Cloud TTS, Azure TTS, AWS Polly).
- Audio is cached in R2/Cloudflare and served as static assets.
- Only **public, non-PII, authored text** is sent for synthesis. No tenant documents, no user inputs.
- A `TTS_AUDIO_BASE_URL` env var points to the cache.
- Cost estimate required before implementation.

## 7. V3 — Tenant-Specific Document Explanation TTS (Optional)

**Trigger:** Document Center users ask for spoken explanations and V2 quality is proven.

- Use **browser `speechSynthesis`** for document explanations to avoid sending user document text to a cloud service.
- Or, if cloud is required, deploy a self-hosted open-source TTS (e.g., [Piper](https://github.com/rhasspy/piper)) inside Semptify infra so text never leaves the tenant trust boundary.

## 8. Out of Scope

- Phone / call-in IVR.
- Real-time two-way voice conversation.
- AI-generated narrative or "explain like I'm five" adaptation.
- Reading full legal statutes verbatim on state-law pages (V1 only reads short summaries).

## 9. Open Decisions for Brad

1. **Scope of V1:** which pages get TTS first? (Recommended: public landing + in-task guide pages.)
2. **Default state:** should TTS be off-by-default everywhere, or auto-on for first-time users on guide pages?
3. **Icon style:** existing `voice_input.html` uses "🎤 Speak" label. TTS button should use a speaker icon + "Read aloud" text, not a microphone icon, to avoid confusion.
4. **V2 budget:** if V1 voices are too robotic, is there a monthly budget cap for cloud TTS? (Estimate would be prepared before V2 build.)
5. **Document Center explanations:** should spoken explanation of a user's document be V1 (browser) or V3 (self-hosted)?

## 10. Implementation Plan

1. Add `static/js/tts_controller.js`.
2. Add TTS toggle button to `public_base.html` and `gui/base.html` headers.
3. Markup pass on `index.html`, `tenant_get_help.html`, and the three guide page templates (`journal_create_guide.html`, `law_library_get_statute.html`, `eviction_defense_calculate_deadlines.html`) plus `components/ui_composer.html`.
4. Verify with IronBee: confirm no auto-play, controls work, `process_indicator` re-reads on state change.
5. PR, review, merge.

## 11. Success Criteria

- TTS can be turned on and off by the user without page reload.
- On guide pages, it reads the `process_indicator` narration as state changes.
- No audio plays automatically on page load.
- No user-typed or document text is sent off-device in V1.
- ARIA landmarks and labels remain accurate after markup changes.

---

*This is a spec-only document. Code implementation is gated on Brad's answers to the open decisions in §9.*
