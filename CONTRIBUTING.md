# Contributing to Semptify

Thanks for considering it. Semptify is a public utility, not a product — a
nonprofit tenant rights tool. Every contribution goes through human review
before it ships.

A few things worth knowing up front:

- This codebase is built primarily through AI coding agents (Devin and
  others), with human review on every change. If you're contributing by
  hand, that's great too — just know the conventions may look agent-shaped
  in places.
- One task per commit. No self-approval on PRs.
- Please read `AGENTS.md` before touching agent-related tooling.

## Ways to give time

- **Code** — pick an open issue, especially ones tagged `good first issue`,
  and open a pull request that links it.
- **Review** — read a public page or guide and tell us what is unclear,
  wrong, or out of date. Plain-language review is real help.
- **Testing** — run the site, try to break it, and file what broke and the
  steps that caused it.
- **Translation** — not open yet. Real translations are deferred until they
  can be done properly; bilingual reviewers are welcome to watch the repo.
- **Listing a resource** — every outside resource Semptify lists (legal aid
  offices, tenant groups) is reviewed and approved by a person before it
  appears. Suggestions go through GitHub or the site's contact page.

## Ground rules — these are not negotiable

- **Python 3.11.9.** The whole codebase is pinned to it. Nothing that
  requires a newer version.
- **Voice and language rules.** No "free" for Semptify itself, no
  business-model words (account, sign up, subscription, pricing), no
  adversarial wording in public copy, no urgency or engagement tactics.
  Plain, calm language — the readers are people in housing crisis.
- **No tenant PII server-side.** A tenant's records live in their own cloud
  storage. New features respect that model; they don't route around it.
- **No dead ends.** Every page, error state, and unfinished feature routes
  the person toward real help.
- **No accounts, ads, tracking, or engagement mechanics.** If a change
  serves the organization instead of the person in crisis, it doesn't ship.
- **Module work goes through the contracts.** Capabilities are declared via
  `FunctionGroupContract`, and new modules start `dev_only` in the Forge.
  See `docs/SDK_GUIDE.md` for the developer kit.
- **Honest status.** If a page mentions a service, it has an entry in the
  Toolbox catalog (`app/modules/portal/toolbox.py`) first — nothing gets
  promised that isn't there.

## Getting started

1. Fork the repo.
2. Set up a local copy — `docs/SELF_HOST.md` has the three-minute version
   (Python 3.11, venv, `pip install -r requirements.txt`, open mode).
3. Check open issues, especially `good first issue`.
4. Open a PR that links the issue. Expect review questions — the bar is
   "safe for someone in crisis to use."

## Verification before you open the PR

- `python -m py_compile` on every Python file you changed.
- `python tools/guardrail_engine.py` — the honesty/structure checks.
- `pytest tests/module_health -q --no-cov` if you touched a module.

## Questions

Open a GitHub Discussion, or reach out through the contact page on
semptify.org.
