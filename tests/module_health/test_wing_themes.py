"""Wing theme guardrails — every audience has one theme file + one archetype.

Mirrors tools/checks/wing_theme_check.py for the pytest suite. The shared
base rule (wing-base.css) is what's tested here, not visual output.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
THEMES = REPO / "static" / "css" / "themes"
ARCHS = REPO / "static" / "css" / "archetypes"

# wing -> (theme file, data-theme value, archetype file)
WINGS = {
    "renters": ("wing-renters.css", "renters", "calm-desk.css"),
    "bill": ("northstar.css", "northstar", "editorial.css"),
    "providers": ("wing-providers.css", "providers", "plain-dealing.css"),
    "advocates": ("wing-advocates.css", "advocates", "field-guide.css"),
    "legal": ("wing-legal.css", "legal", "brief.css"),
    "research": ("wing-research.css", "research", "ledger.css"),
    "classroom": ("wing-classroom.css", "classroom", "classroom.css"),
    "developers": ("wing-developers.css", "developers", "docs.css"),
    "supporters": ("wing-supporters.css", "supporters", "open-report.css"),
}

REQUIRED_TOKENS = ("--role-accent", "--role-deep", "--role-tint", "--shell-sage")
STATUS_TOKENS = ("--color-success", "--color-warning", "--color-error",
                 "--color-info", "--color-alarm")


def test_every_wing_has_theme_and_archetype():
    for wing, (theme_name, _dt, arch_name) in WINGS.items():
        assert (THEMES / theme_name).exists(), f"{wing}: {theme_name} missing"
        assert (ARCHS / arch_name).exists(), f"{wing}: {arch_name} missing"


def test_theme_files_set_wing_surface():
    for wing, (theme_name, data_theme, _a) in WINGS.items():
        css = (THEMES / theme_name).read_text(encoding="utf-8")
        assert f'[data-theme="{data_theme}"]' in css, theme_name
        for token in REQUIRED_TOKENS:
            assert token in css, f"{theme_name}: {token} missing"


def test_theme_files_have_dark_pin():
    for wing, (theme_name, data_theme, _a) in WINGS.items():
        css = (THEMES / theme_name).read_text(encoding="utf-8")
        assert "prefers-color-scheme" in css, theme_name
        dark_block = css.split("prefers-color-scheme")[-1]
        assert f'[data-theme="{data_theme}"]' in dark_block, theme_name


def test_no_wing_redefines_status_semantics():
    for wing, (theme_name, _dt, _a) in WINGS.items():
        css = (THEMES / theme_name).read_text(encoding="utf-8")
        for token in STATUS_TOKENS:
            assert not re.search(re.escape(token) + r"\s*:", css), (
                f"{theme_name} redefines reserved {token}")


def test_archetype_files_key_on_data_arch():
    for wing, (_t, _dt, arch_name) in WINGS.items():
        css = (ARCHS / arch_name).read_text(encoding="utf-8")
        arch_id = arch_name.removesuffix(".css")
        assert f'[data-arch="{arch_id}"]' in css, arch_name


def test_wing_base_contract_file_exists():
    base = THEMES / "wing-base.css"
    assert base.exists()
    text = base.read_text(encoding="utf-8")
    # The shared base rule must name its four invariants.
    for phrase in ("Get help now", "one organization", "status"):
        assert phrase.lower() in text.lower()


def test_toolbox_wings_resolve_to_themes():
    """When the toolbox catalog is present, every non-shared wing maps."""
    toolbox_py = REPO / "app" / "modules" / "portal" / "toolbox.py"
    if not toolbox_py.exists():
        return  # catalog lands with feat/toolbox-service-stubs
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location("toolbox_mod", toolbox_py)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["toolbox_mod"] = mod
    spec.loader.exec_module(mod)
    for wing in getattr(mod, "WINGS", ()):
        if wing == "shared":
            continue
        assert wing in WINGS, f"toolbox wing '{wing}' has no theme file"
