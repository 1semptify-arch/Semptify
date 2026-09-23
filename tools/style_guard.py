#!/usr/bin/env python3
"""Style guard — stop visual drift at the door.

Semptify's design system lives in `static/css/ssot-design-system.css`. Pages
must style with `var(--token)` references, not hardcoded colors, and text must
not drop below the 12px / 0.75rem readability floor. This tool enforces both.

Checks (inside <style> blocks and style="..." attributes of HTML templates,
and everywhere in non-allowlisted .css files):

  1. Hardcoded hex colors (#rgb / #rrggbb / #rrggbbaa) — bypass the token
     system and silently drift when the palette changes. Hex values inside a
     var() fallback (`var(--token, #fff)`) are allowed: the token still wins.
  2. font-size below the floor (< 0.75rem or < 12px, excluding 0 which is an
     intentional layout trick).

Allowlisted files (hex colors are their job):
  - static/css/ssot-design-system.css   (the token source of truth)
  - static/css/themes/*                 (legacy theme switcher palettes)
  - static/design-system.css            (deprecated parallel system, pending
                                         fold-or-archive decision 10.2)

Known existing violations are recorded in tools/style_guard_baseline.json so
CI stays green while debt is paid down. A file may have AT MOST its baseline
count — any new violation, or a violation in a non-baselined file, fails.

Usage:
  python tools/style_guard.py                 # check (exit 1 on violations)
  python tools/style_guard.py --write-baseline # regenerate baseline (intentional!)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = ROOT / "tools" / "style_guard_baseline.json"

SCAN_GLOBS = [
    "app/templates/**/*.html",
    "app/static/**/*.css",
    "static/**/*.css",
    "static/**/*.html",
]

# Files whose job is to define literal colors.
HEX_ALLOWLIST = {
    "static/css/ssot-design-system.css",
    "static/design-system.css",
}
HEX_ALLOWLIST_PREFIXES = ("static/css/themes/",)

MIN_REM = 0.75
MIN_PX = 12.0

_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
# var(--token, <fallback>) — strip before scanning so fallbacks are allowed.
# Handles one level of nested parens, which is all these files need.
_VAR_CALL = re.compile(r"var\((?:[^()]|\([^()]*\))*\)")
_FONT_REM = re.compile(r"font-size\s*:\s*0\.(\d+)rem", re.IGNORECASE)
_FONT_PX = re.compile(r"font-size\s*:\s*(\d+(?:\.\d+)?)px", re.IGNORECASE)
_STYLE_ATTR = re.compile(r'style\s*=\s*"([^"]*)"', re.IGNORECASE | re.DOTALL)
_STYLE_ATTR_SQ = re.compile(r"style\s*=\s*'([^']*)'", re.IGNORECASE | re.DOTALL)
_STYLE_BLOCK = re.compile(r"<style[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)


def _style_fragments(text: str, is_html: bool) -> list[str]:
    """Return the CSS-bearing fragments of a file."""
    if not is_html:
        return [text]
    frags = _STYLE_BLOCK.findall(text)
    frags += _STYLE_ATTR.findall(text)
    frags += _STYLE_ATTR_SQ.findall(text)
    return frags


def _count_violations(path: Path, rel: str) -> tuple[int, list[str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    is_html = path.suffix.lower() == ".html"
    allow_hex = rel in HEX_ALLOWLIST or any(
        rel.startswith(p) for p in HEX_ALLOWLIST_PREFIXES
    )

    violations: list[str] = []
    for frag in _style_fragments(text, is_html):
        stripped = _VAR_CALL.sub("var(--x)", frag)
        if not allow_hex:
            for m in _HEX.finditer(stripped):
                # Only value position: preceded by :, (, =, ", or '.
                # ID selectors like #dcEmptyUploadBtn sit at declaration
                # start (preceded by { } newline , >) and are ignored.
                i = m.start()
                j = i - 1
                while j >= 0 and stripped[j] in " \t":
                    j -= 1
                prev = stripped[j] if j >= 0 else ""
                if prev in ":('\"=":
                    violations.append(f"hardcoded color {m.group(0)}")
        for m in _FONT_REM.finditer(frag):
            if 0 < float("0." + m.group(1)) < MIN_REM:
                violations.append(f"font-size {m.group(0).split(':')[1].strip()}")
        for m in _FONT_PX.finditer(frag):
            v = float(m.group(1))
            if 0 < v < MIN_PX:
                violations.append(f"font-size {m.group(0).split(':')[1].strip()}")
    return len(violations), violations


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for pattern in SCAN_GLOBS:
        files.extend(ROOT.glob(pattern))
    return sorted(set(files))


def main() -> int:
    baseline: dict[str, int] = {}
    if BASELINE_PATH.exists():
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    current: dict[str, int] = {}
    details: dict[str, list[str]] = {}
    for path in _iter_files():
        rel = path.relative_to(ROOT).as_posix()
        count, found = _count_violations(path, rel)
        if count:
            current[rel] = count
            details[rel] = found

    if "--write-baseline" in sys.argv:
        BASELINE_PATH.write_text(
            json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"Baseline written: {sum(current.values())} violations across {len(current)} files")
        return 0

    failures = 0
    for rel, count in sorted(current.items()):
        allowed = baseline.get(rel, 0)
        if count > allowed:
            failures += 1
            print(f"FAIL {rel}: {count} violations (baseline allows {allowed})")
            for v in details[rel][:10]:
                print(f"      - {v}")
            if count > 10:
                print(f"      ... and {count - 10} more")
        elif count < allowed:
            print(f"IMPROVED {rel}: {count} violations (baseline was {allowed}) — "
                  f"regenerate baseline with --write-baseline")
        else:
            print(f"ok*  {rel}: {count} violations (at baseline)")

    if failures:
        print()
        print("Style guard failed. Use var(--token) colors from "
              "static/css/ssot-design-system.css and keep font-size >= 0.75rem / 12px.")
        return 1

    print(f"Style guard passed ({sum(current.values())} baselined violations, 0 new).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
