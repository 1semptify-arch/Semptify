# Languages Prep Blueprint (P4 scope: "languages-prep")

**Status:** DRAFT — pending approval
**Type:** Approach decision + small honesty fix (translation build itself
is P8)
**Pillar:** KNOW
**Tier:** L0 public
**Date:** 2026-11-06
**Toolbox entry:** `languages` (planned, group=know, engine=content) —
"Semptify in the languages tenants actually speak." P8 owns real
translations; P4's job is the prep so P8 starts on rails, not on
archaeology.

## Live state (verified against code)

- `app/core/i18n.py` — working machinery: JSON catalogs in
  `app/translations/`, locale resolution (arg → `semptify_locale` cookie →
  Accept-Language → env → `en`), `gettext`/`ngettext` Jinja helpers,
  `_meta.status: "human_reviewed"` marker support, English fallback.
- `app/translations/` — **14 catalogs, ~23 keys each** (en 24). es/hmn/
  so/ar checked: all marked `_meta.status: "machine"` — "machine
  translation pending human review." UI chrome keys only
  (`brand.name`, `action.get_help`, `action.continue`…).
- `components/locale_selector.html` + `GET/POST /api/i18n/*` exist;
  the selector is wired into base templates.
- **The gap:** public pages are hardcoded English — almost nothing under
  `app/templates/public/` or `body/public_shell.html` calls `gettext`.
  The catalogs cover chrome strings, not the long-form prose that is the
  actual content of pages like `/credit-reports` or `/help`.
- The toolbox `note` is **stale**: it says "12 language files exist as
  empty placeholders." Reality: 14 files, ~23 keys each, machine-
  translated pending human review — not empty, but far from usable.

## The decision that makes P8 cheap

P8 will face one fork; picking now keeps the prep aligned:

- **Option A — gettext-everything.** Wrap every public-page string in
  `{{ _("key") }}` and explode catalogs to hundreds of keys per locale.
  Idiomatic, but Semptify's public pages are long-form prose (guide
  paragraphs, disclaimers, letters) — key-per-sentence catalogs rot fast,
  read badly for translators, and every copy edit becomes a key change.
- **Option B — per-page content catalogs (recommended).** Keep gettext
  for chrome (what exists today), and for public *content* pages store
  whole-page translations as parallel content (e.g.
  `app/translations/pages/credit_reports.es.html` or a per-page JSON of
  named blocks), resolved by locale at render with English fallback.
  Translators see whole paragraphs in context — which is what produces
  *correct, human* translations of plain-language legal-adjacent prose —
  and copy stays reviewable as prose, not as 400 keys. The locale
  machinery is already in place; this is a template-resolution pattern,
  not new infrastructure.

Either way, P8 needs a **review rule** the prep should set now: a
catalog/page translation is only shown to visitors after a human marks
`_meta.status: "human_reviewed"` (the field already exists for exactly
this). Machine drafts stay invisible — same BETA/VETTED honesty rule as
content (see `content_review_next_states_blueprint.md`).

## Also decided by this blueprint (small, do now)

- **Toolbox note correction** (with the toolbox-branch flip batch, or a
  one-line edit on that branch now): replace "12 language files exist as
  empty placeholders" with the truthful state — "A language switcher and
  14 starter catalogs exist; page content is English-only until
  translations are human-reviewed."
- **Locale-selector visibility.** Right now the selector offers 13
  languages that each cover ~23 chrome strings — selecting Somali changes
  almost nothing a visitor sees. Options: (a) hide the selector until a
  first page is human_reviewed (recommended — a control that changes
  nothing is a soft dead end), or (b) leave it and accept the shallow
  coverage. This is a two-line template guard either way.

## Decision needed (Brad)

1. Catalog architecture: Option A vs. B (recommended B).
2. Hide the locale selector until first human-reviewed page vs. leave it
   (recommended: hide).
3. First locales to commission for P8 — es/hmn/so/ar are the seeded four
   and match MN tenant demographics; confirm or reorder.

## Scope if approved (P8 build pass — not this task)

- Template-resolution pattern for per-page catalogs (Option B) + loader
  tests.
- Translate `/help`, `/credit-reports`, `/start-a-tenant-group`, and the
  `/preamble` entry pages first — highest Time-to-Real-Help value.
- `languages` toolbox flip when the first human-reviewed page ships.

## Verification (for the build pass)

- `POST /api/i18n/set-locale` + reload shows translated content only
  where `_meta.status == "human_reviewed"`; English elsewhere.
- No key missing errors in logs; fallback silent as designed.
