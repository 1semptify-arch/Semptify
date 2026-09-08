"""Legacy pages/ reachability audit — read-only classification.

For every app/templates/pages/*.html file:
  - Is it in PAGE_MANIFEST (page_id, route, page_type, coverage, priority)?
  - Is it referenced anywhere else (routers, TemplateResponse, includes)?
  - What does it extend (new body/* pattern vs legacy chrome vs standalone)?

Output: markdown triage table to stdout.

Read-only. Does not modify anything.
"""

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PAGES_DIR = BASE / "app" / "templates" / "pages"
MANIFEST = BASE / "app" / "core" / "page_manifest.py"
NAV = BASE / "app" / "core" / "navigation.py"

# ---------------------------------------------------------------- manifest --

text = MANIFEST.read_text(encoding="utf-8")
entries = []
# Each entry is a PageManifestEntry(...) block; split on the constructor call.
for block in re.split(r"PageManifestEntry\(", text)[1:]:
    def field(name, default=""):
        m = re.search(rf'{name}\s*=\s*"([^"]*)"', block)
        return m.group(1) if m else default
    def field_raw(name, default=""):
        m = re.search(rf'{name}\s*=\s*([^,\)]+)', block)
        return m.group(1).strip() if m else default
    entries.append({
        "page_id": field("page_id"),
        "route": field("route"),
        "source_file": field("source_file"),
        "page_type": field("page_type"),
        "coverage": field_raw("overall_coverage").replace("CoverageStatus.", ""),
        "priority": field("recommended_priority"),
    })

manifest_by_file = {}
for e in entries:
    manifest_by_file[e["source_file"].replace("\\", "/")] = e

# ------------------------------------------------------- search corpus -----
# All Python + HTML + JS sources that could reference a page template.
search_files = []
for ext in ("*.py", "*.html", "*.js", "*.md"):
    for p in BASE.rglob(ext):
        sp = str(p)
        if any(skip in sp for skip in (
            "venv311", "node_modules", "__pycache__", ".git\\",
            "htmlcov", ".pytest_cache", ".mypy_cache", ".ruff_cache",
        )):
            continue
        search_files.append(p)

file_text_cache: dict[str, str] = {}

def haystack() -> str:
    # One big string is fine for substring counting; cache once.
    if "_all" not in file_text_cache:
        parts = []
        for p in search_files:
            try:
                parts.append(p.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                pass
        file_text_cache["_all"] = "\n".join(parts)
    return file_text_cache["_all"]

ALL_TEXT = haystack()

# navigation.py stage paths (for "reachable via tenant navigation" check)
nav_text = NAV.read_text(encoding="utf-8") if NAV.exists() else ""
nav_paths = set(re.findall(r'path\s*=\s*"([^"]+)"', nav_text))
nav_paths |= set(re.findall(r'"(/[A-Za-z0-9_\-/{}]+)"', nav_text))

# page_router skip list (routes with dedicated handlers elsewhere)
pr = (BASE / "app" / "modules" / "page_router" / "router.py").read_text(encoding="utf-8")
skip_block = re.search(r"_SKIP_ROUTES\s*=\s*\{(.*?)\}", pr, re.S).group(1)
skip_routes = set(re.findall(r'"(/[^"]*)"', skip_block))

# ------------------------------------------------------------------ audit --

rows = []
for f in sorted(PAGES_DIR.glob("*.html")):
    name = f.name
    rel = f"app/templates/pages/{name}"
    src = f.read_text(encoding="utf-8", errors="replace")

    m = re.search(r'{%\s*extends\s+"([^"]+)"', src)
    extends = m.group(1) if m else "(none)"

    man = manifest_by_file.get(rel)

    # references: count of the filename or path outside the file itself
    refs = 0
    for probe in (f"pages/{name}", name):
        refs = max(refs, ALL_TEXT.count(probe))
    # subtract self-reference (the file is in the corpus)
    if f'pages/{name}' in src or name in src:
        refs -= 1
    refs = max(0, refs)

    # where referenced (rough): which dirs
    ref_dirs = set()
    for p in search_files:
        if p == f:
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if f"pages/{name}" in t:
            ref_dirs.add(str(p.parent.relative_to(BASE)).split("\\")[0])

    in_nav = bool(man and man["route"] in nav_paths)
    skipped = bool(man and man["route"] in skip_routes)

    rows.append({
        "file": name,
        "extends": extends,
        "page_id": man["page_id"] if man else "",
        "route": man["route"] if man else "",
        "coverage": man["coverage"] if man else "",
        "priority": man["priority"] if man else "",
        "manifest": bool(man),
        "skipped_dedicated": skipped,
        "in_nav": in_nav,
        "refs": refs,
        "ref_dirs": sorted(ref_dirs),
        "exists": True,
    })

# manifest entries pointing at missing files
missing = [e for e in entries
           if e["source_file"].startswith("app/templates")
           and not (BASE / e["source_file"]).is_file()]

print(json.dumps({"rows": rows, "manifest_entries": len(entries),
                  "missing_template_entries": missing}, indent=1))
