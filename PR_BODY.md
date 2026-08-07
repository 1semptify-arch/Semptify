# Summary

Automated markdown lint fixes across the repo. No logic changes.

- Convert emphasis-style headings to ATX headings across all `.md` files.
- Add language tags to fenced code blocks where inferrable.
- Normalize table separator spacing and missing blank lines around blocks.
- Add `.markdownlint-cli2.jsonc` config.
- Resolve MD036/MD040 warnings in `docs/admin/Semptify_Site_GUI_Framework.md`.
- Remove one-off `fix_md_manual.py` script after the pass completed.

**Scope:** 278 files changed, +10356 / -4431. Pure markdown formatting — whitespace, heading syntax, code fence language tags, table padding, blank lines around blocks. No source code, no templates, no config logic.

**Known:** 5 trailing-whitespace lines remain in archive/data files (intentional `<br>` breaks), and many bare code fences still need language tags — out of scope for this pass.

## Test plan

- [ ] CI passes (pre-commit, Bandit, pytest) — this is the first large diff against the newly enforced CI gates
- [ ] No `.py` / `.html` / `.yaml` logic files changed (only `.md` and the removed one-off script)
- [ ] Spot-check a few large `.md` files (BUILD_STATE.md, AGENTS.md, README.md) for rendering correctness

Generated with [Devin](https://devin.ai)
