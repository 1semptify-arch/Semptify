"""Text-contrast guard (WCAG AA 4.5:1) for the public/shell design system.

Brad's rule (2026-11-03): light text on a light background is a bug. This test
fails if a text token or a hard-coded `color:` literal in the public templates
and design-system CSS drops below 4.5:1 on the light-theme surfaces.

Run: python tests/test_text_contrast.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT_SURFACES = {"paper": "#f6f4ef", "card": "#efeeea", "white": "#ffffff"}
MIN = 4.5
SKIP_DARK_CONTEXT = re.compile(r"dark|--shell-ink-[23]\s*:\s*#(b6b1a8|8f897f)", re.I)


def _lum(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    chans = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in chans]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a: str, b: str) -> float:
    hi, lo = sorted([_lum(a), _lum(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _worst(color: str) -> float:
    return min(ratio(color, s) for s in LIGHT_SURFACES.values())


def check_tokens() -> list[str]:
    css = (ROOT / "static/css/ssot-design-system.css").read_text(encoding="utf-8")
    problems = []
    for token in ("--text-secondary", "--text-muted"):
        m = re.search(rf"^\s*{token}:\s*(#[0-9a-fA-F]{{6}});", css, re.M)
        if m and _worst(m.group(1)) < MIN:
            problems.append(f"{token} {m.group(1)} = {_worst(m.group(1)):.2f}:1 on worst light surface")
    for m in re.finditer(r"^\s*--shell-ink-([23]):\s*(#[0-9a-fA-F]{6});", css, re.M):
        line_start = css.rfind("\n", 0, m.start())
        ctx = css[max(0, line_start - 400) : m.start()]
        if "prefers-color-scheme: dark" in ctx[-250:] or "data-theme=\"dark\"" in ctx[-250:]:
            continue
        if m.group(2).lower() in ("#b6b1a8", "#8f897f"):
            continue
        if _worst(m.group(2)) < MIN:
            problems.append(f"--shell-ink-{m.group(1)} {m.group(2)} = {_worst(m.group(2)):.2f}:1")
    return problems


def check_filled_controls() -> list[str]:
    """Light text on a filled control: inverse text over the accent fill."""
    problems = []
    for name, fg, bg in (
        ("cta on role-deep", "#fbfaf8", "#4c6b4c"),
        ("cta on sage-solid", "#fbfaf8", "#527052"),
    ):
        if ratio(fg, bg) < MIN:
            problems.append(f"{name} = {ratio(fg, bg):.2f}:1")
    return problems


def check_literals(report_only: bool = False) -> list[str]:
    pat = re.compile(r"(?<![-\w])color\s*:\s*(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})\b")
    problems = []
    files = [p for p in (ROOT / "app/templates/public").glob("*.html") if p.name != "donate.html"] + [
        ROOT / "app/templates/body/public_shell.html",
        ROOT / "app/templates/public_base.html",
    ]
    for f in files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        for m in pat.finditer(text):
            c = m.group(1)
            line_no = text.count("\n", 0, m.start()) + 1
            line = text.splitlines()[line_no - 1]
            if _lum(c) < 0.25:
                continue
            if "background" in line and c.lower() in line.lower().split("background")[1]:
                continue
            if SKIP_DARK_CONTEXT.search(text[max(0, m.start() - 300) : m.start()]):
                continue
            if _worst(c) < MIN and _lum(c) > 0.30:
                problems.append(f"{f.relative_to(ROOT)}:{line_no} color {c} = {_worst(c):.2f}:1")
    return problems


def check_donate_dark() -> list[str]:
    """donate.html is a self-contained dark page: check its text vars on its own surfaces."""
    text = (ROOT / "app/templates/public/donate.html").read_text(encoding="utf-8")
    surfaces = [re.search(rf"--{n}:\s*(#[0-9a-fA-F]{{6}})", text).group(1) for n in ("bg", "card-bg", "card-bg2")]
    problems = []
    for var in ("text", "muted", "teal", "green"):
        fg = re.search(rf"--{var}:\s*(#[0-9a-fA-F]{{6}})", text).group(1)
        worst = min(ratio(fg, s) for s in surfaces)
        if worst < MIN:
            problems.append(f"donate.html --{var} {fg} = {worst:.2f}:1 on dark surfaces")
    return problems


def main() -> int:
    problems = check_tokens() + check_filled_controls() + check_literals() + check_donate_dark()
    for p in problems:
        print("FAIL", p)
    print("OK: all checked text >= 4.5:1" if not problems else f"{len(problems)} contrast problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
