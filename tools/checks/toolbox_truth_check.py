"""
toolbox_truth_check.py — claims-vs-live guardrail for the Toolbox catalog.

The Toolbox catalog (app/modules/portal/toolbox.py) is the SSOT for every
service semptify.org mentions. This check mechanically enforces the rule
"no public page claims more than the catalog says" at the level a script
can verify:

1. Catalog structure is valid — unique ids, valid status/level/engine/group,
   non-empty purpose and `today` text on every entry.
2. Every internal `today_path` and every `promised_on` path resolves to a
   real public surface: the portal pages registry, a verified allowlist of
   app/worker routes, or the generated /toolbox pages themselves.
3. Every `backed_by` name resolves to a real module directory under
   app/modules/ (or app/services/<name>) — nothing is claimed to be backed
   by code that does not exist.
4. No public template links to /toolbox/<id> for an id missing from the
   catalog — a linked toolbox page must exist.

What this check does NOT do (documented limits):
- It cannot read prose claims inside pages (e.g. "35 states") and compare
  them to reality — that stays a human/editorial job, aided by `note`
  fields in the catalog.
- It skips cleanly on branches where the toolbox catalog does not exist,
  so it is safe for the shared guardrail engine on every branch.
"""

import importlib.util
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from guardrail_engine import CheckResult  # noqa: E402

TOOLBOX_PATH = Path("app/modules/portal/toolbox.py")
PAGES_PATH = Path("app/modules/portal/pages.py")
PUBLIC_TEMPLATES = Path("app/templates/public")

# Public paths that are real but not in the portal pages registry — verified
# against route code on feat/toolbox-service-stubs (2026-11-06):
#   /                     welcome page served at root
#   /preamble             app/modules/preamble/router.py
#   /law-library          app/modules/law_library/router.py:1983
#   /library              app/main.py + app/modules/page_router allowlist
#   /eviction-defense     app/main.py:4029
#   /bill, /bill/live, /bill/research   bill-mirror Cloudflare worker (not an app route)
KNOWN_PUBLIC_PATHS = {
    "/",
    "/preamble",
    "/law-library",
    "/library",
    "/eviction-defense",
    "/bill",
    "/bill/live",
    "/bill/research",
}


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves cls.__module__ via sys.modules — register before exec.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _registry_paths(repo_root: Path) -> set[str]:
    """Paths of every page registered in the portal pages registry."""
    pages_file = repo_root / PAGES_PATH
    if not pages_file.exists():
        return set()
    mod = _load_module(pages_file, "portal_pages_registry_check")
    return {p.path for p in mod.PortalPageRegistry.PAGES}


def run(repo_root: Path) -> CheckResult:
    toolbox_file = repo_root / TOOLBOX_PATH
    if not toolbox_file.exists():
        return CheckResult(
            name="toolbox_truth_check",
            passed=True,
            summary="toolbox catalog not present on this branch — skipped.",
        )

    mod = _load_module(toolbox_file, "toolbox_catalog_check")
    entries = mod.ToolboxCatalog.ENTRIES
    valid_status = set(mod.STATUSES)
    valid_level = set(mod.LEVELS)
    valid_engine = set(mod.ENGINES)
    valid_group = set(mod.ToolboxCatalog.GROUPS)

    resolvable = _registry_paths(repo_root) | KNOWN_PUBLIC_PATHS | {"/toolbox"}
    resolvable |= {f"/toolbox/{e.id}" for e in entries}
    catalog_ids = {e.id for e in entries}

    problems: list[str] = []

    # 1. Structure
    if len(catalog_ids) != len(entries):
        seen, dup = set(), set()
        for e in entries:
            (dup if e.id in seen else seen).add(e.id)
        problems.append(f"duplicate entry id(s): {sorted(dup)}")

    for e in entries:
        if e.status not in valid_status:
            problems.append(f"{e.id}: invalid status '{e.status}'")
        if e.level not in valid_level:
            problems.append(f"{e.id}: invalid level '{e.level}'")
        if e.engine not in valid_engine:
            problems.append(f"{e.id}: invalid engine '{e.engine}'")
        if e.group not in valid_group:
            problems.append(f"{e.id}: invalid group '{e.group}'")
        if not e.purpose.strip() or not e.today.strip():
            problems.append(f"{e.id}: empty purpose or today text")

    # 2. Internal paths resolve (external links and tel: skipped)
    def _unresolved(path: str) -> bool:
        return path.startswith("/") and path not in resolvable

    for e in entries:
        if _unresolved(e.today_path):
            problems.append(f"{e.id}: today_path '{e.today_path}' resolves to no public page")
        for p in e.promised_on:
            if _unresolved(p):
                problems.append(f"{e.id}: promised_on '{p}' resolves to no public page")

    # 3. backed_by names exist as modules or services
    for e in entries:
        for name in e.backed_by:
            mod_dir = repo_root / "app" / "modules" / name
            svc = repo_root / "app" / "services" / f"{name}.py"
            svc_dir = repo_root / "app" / "services" / name
            if not (mod_dir.is_dir() or svc.is_file() or svc_dir.is_dir()):
                problems.append(f"{e.id}: backed_by '{name}' — no app/modules or app/services match")

    # 4. /toolbox/<id> links in public templates must name real entries
    tpl_dir = repo_root / PUBLIC_TEMPLATES
    if tpl_dir.is_dir():
        link_re = re.compile(r'href="/toolbox/([a-z0-9_]+)"')
        for tpl in sorted(tpl_dir.glob("*.html")):
            for m in link_re.finditer(tpl.read_text(encoding="utf-8", errors="replace")):
                if m.group(1) not in catalog_ids:
                    problems.append(f"{tpl.name}: links /toolbox/{m.group(1)} — no such catalog entry")

    if problems:
        return CheckResult(
            name="toolbox_truth_check",
            passed=False,
            summary=f"{len(problems)} truth problem(s) between the toolbox catalog and the live surface.",
            details="\n".join(problems),
        )

    counts = mod.ToolboxCatalog.counts()
    return CheckResult(
        name="toolbox_truth_check",
        passed=True,
        summary=(
            f"{len(entries)} catalog entries verified — structure valid, all internal paths resolve, "
            f"all backed_by modules exist, no dead /toolbox links. "
            f"({counts.get('live', 0)} live, {counts.get('partial', 0)} partial, "
            f"{counts.get('planned', 0)} planned, {counts.get('vision', 0)} vision)"
        ),
    )
