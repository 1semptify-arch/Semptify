"""
wing_theme_check.py — guardrail for the audience-wing theme system.

Implements the mechanical half of SEMPTIFY_ORG_ARCHITECTURE_DRAFT.md §3
and the shared-base contract in static/css/themes/wing-base.css:

1. Every audience wing has exactly one theme file — wing-<name>.css in
   static/css/themes/ (the bill wing uses the existing northstar.css).
2. Every wing has exactly one layout archetype — <name>.css in
   static/css/archetypes/, applied via `data-arch`.
3. Every wing theme file keys on `[data-theme="<wing>"]`, sets the wing
   accent surface (--role-accent/--role-deep/--role-tint/--shell-sage),
   and ends with a prefers-color-scheme:dark pin so the global dark flip
   cannot break its palette.
4. The shared base rule: no wing file may redefine status semantics
   (--color-success/warning/error/info/alarm) — color means state only.
5. When the toolbox catalog is present (feat/toolbox-service-stubs and
   later), every non-"shared" WINGS value resolves to a theme file, so the
   catalog's wing field can never point at a wing with no theme.

Skips cleanly on branches where the wing theme system has not landed yet.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from guardrail_engine import CheckResult  # noqa: E402

THEMES_DIR = Path("static/css/themes")
ARCHETYPES_DIR = Path("static/css/archetypes")
TOOLBOX_PATH = Path("app/modules/portal/toolbox.py")

# Wing -> (theme file, archetype file). The single source for what the
# draft's §3 table requires on disk. "bill" maps to northstar.css, which
# predates the wing system and stays as-is.
WING_FILES = {
    "renters": ("wing-renters.css", "calm-desk.css"),
    "bill": ("northstar.css", "editorial.css"),
    "providers": ("wing-providers.css", "plain-dealing.css"),
    "advocates": ("wing-advocates.css", "field-guide.css"),
    "legal": ("wing-legal.css", "brief.css"),
    "research": ("wing-research.css", "ledger.css"),
    "classroom": ("wing-classroom.css", "classroom.css"),
    "developers": ("wing-developers.css", "docs.css"),
    "supporters": ("wing-supporters.css", "open-report.css"),
}

# data-theme value -> theme file key, for files that don't follow the
# wing-<name> convention (the bill wing's northstar.css).
DATA_THEME_NAMES = {
    "renters": "renters",
    "bill": "northstar",
    "providers": "providers",
    "advocates": "advocates",
    "legal": "legal",
    "research": "research",
    "classroom": "classroom",
    "developers": "developers",
    "supporters": "supporters",
}

REQUIRED_TOKENS = ("--role-accent", "--role-deep", "--role-tint", "--shell-sage")
STATUS_TOKENS = ("--color-success", "--color-warning", "--color-error",
                 "--color-info", "--color-alarm")


def _toolbox_wings(repo_root: Path) -> set[str]:
    """Non-'shared' wing ids from the toolbox catalog, if it exists."""
    toolbox_file = repo_root / TOOLBOX_PATH
    if not toolbox_file.exists():
        return set()
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "toolbox_wings_check", toolbox_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules["toolbox_wings_check"] = module
        spec.loader.exec_module(module)
        return {w for w in getattr(module, "WINGS", ()) if w != "shared"}
    except Exception:
        return set()


def run(repo_root: Path) -> CheckResult:
    themes_dir = repo_root / THEMES_DIR
    if not (themes_dir / "wing-base.css").exists():
        return CheckResult(
            name="wing_theme_check",
            passed=True,
            summary="wing theme system not present on this branch — skipped.",
        )

    problems: list[str] = []

    # 1 + 2. Theme and archetype files exist for every wing.
    for wing, (theme_name, arch_name) in WING_FILES.items():
        theme_file = themes_dir / theme_name
        arch_file = repo_root / ARCHETYPES_DIR / arch_name
        if not theme_file.exists():
            problems.append(f"wing '{wing}': missing theme file {theme_name}")
            continue
        if not arch_file.exists():
            problems.append(
                f"wing '{wing}': missing archetype file {arch_name}")

        # 3. Theme file contract.
        css = theme_file.read_text(encoding="utf-8")
        data_theme = DATA_THEME_NAMES[wing]
        if f'[data-theme="{data_theme}"]' not in css:
            problems.append(
                f"{theme_name}: no [data-theme=\"{data_theme}\"] selector")
        for token in REQUIRED_TOKENS:
            if token not in css:
                problems.append(f"{theme_name}: missing {token}")
        if "prefers-color-scheme" not in css or "dark" not in css:
            problems.append(f"{theme_name}: missing dark-mode pin")
        elif f'[data-theme="{data_theme}"]' not in css.split(
                "prefers-color-scheme")[-1]:
            problems.append(
                f"{theme_name}: dark-mode pin not scoped to data-theme")

        # 4. Shared base rule — status semantics are reserved.
        for token in STATUS_TOKENS:
            if re.search(re.escape(token) + r"\s*:", css):
                problems.append(
                    f"{theme_name}: redefines reserved status token {token}")

        # Archetype file contract.
        if arch_file.exists():
            arch_css = arch_file.read_text(encoding="utf-8")
            arch_id = arch_name.removesuffix(".css")
            if f'[data-arch="{arch_id}"]' not in arch_css:
                problems.append(
                    f"{arch_name}: no [data-arch=\"{arch_id}\"] selector")

    # 5. Toolbox wings all resolve to a theme file.
    for wing in _toolbox_wings(repo_root):
        if wing not in WING_FILES:
            problems.append(
                f"toolbox WINGS entry '{wing}' has no theme file mapping")

    if problems:
        return CheckResult(
            name="wing_theme_check",
            passed=False,
            summary=f"{len(problems)} problem(s): " + "; ".join(problems),
        )
    return CheckResult(
        name="wing_theme_check",
        passed=True,
        summary=f"{len(WING_FILES)} wings: theme + archetype files verified.",
    )
