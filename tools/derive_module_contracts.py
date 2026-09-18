"""Derive module_contract.json files from registered FunctionGroupContracts.

Implements the SEMPTIFY_BUILD_CONTRACT [AMENDED] rule: where fields overlap,
module contract data is generated from the registered runtime contract rather
than independently hand-authored.

What is derived (real data from FunctionGroupContract):
- module_name: humanized module dir name
- inputs: merged across the module's function groups; `name?` marks optional
- input_audit: one entry per input (source "other" — real source not in FGC)
- output_how / output_where: from allowed_routes / allowed_prefixes
- process_description: concatenated group descriptions

What is honestly generic (FGC has no data for it):
- layout, output_why, process_context — marked "Derived record" so a human
  can polish them later without mistaking them for authored content
- output_type: "other" — the FGC schema has no output classification
- preview_state / review_state: left null (only required for
  ui_state_change/notification output types)
- narrative_events: empty — verbs cannot be derived from FGC data

Usage (from module root, venv311):
    python tools/derive_module_contracts.py --dry-run          # report only
    python tools/derive_module_contracts.py --only journal vault
    python tools/derive_module_contracts.py --write            # all eligible
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MODULE_ROOT))

MODULES_DIR = MODULE_ROOT / "app" / "modules"


def humanize(dirname: str) -> str:
    return dirname.replace("_", " ").replace("-", " ").title()


def derive(module_dir: Path, groups: list) -> dict:
    """Build one module_contract.json dict from a module's FGC groups."""
    mod = module_dir.name

    # Merge inputs across groups; `name?` = optional in that group.
    # required=True only when the input is non-optional everywhere it appears.
    inputs: dict[str, bool] = {}
    for g in groups:
        for raw in g.inputs:
            optional = raw.endswith("?")
            name = (raw[:-1] if optional else raw).strip()
            if not name:
                continue
            inputs[name] = inputs.get(name, True) and not optional

    routes = sorted({r for g in groups for r in g.allowed_routes})
    prefixes = sorted({p for g in groups for p in g.allowed_prefixes})
    outputs = sorted({o for g in groups for o in g.outputs})
    group_names = ", ".join(g.group_name for g in groups)

    where = ", ".join(routes) if routes else f"app.modules.{mod} function outputs"
    if prefixes:
        where += f" (prefixes: {', '.join(prefixes)})"

    return {
        "module_name": humanize(mod),
        "layout": (
            f"app/modules/{mod}/ — {len(groups)} registered function groups "
            f"({group_names}). Derived record: page layout not yet described."
        ),
        "inputs": [
            {"name": n, "type": "field", "required": req}
            for n, req in sorted(inputs.items())
        ],
        "input_audit": [
            {
                "input_name": n,
                "source": "other",
                "note": "Derived from FunctionGroupContract; real input source "
                "not yet recorded.",
            }
            for n in sorted(inputs)
        ],
        "preview_state": None,
        "review_state": None,
        "output_type": "other",
        "output_how": (
            f"Registered function groups return named outputs "
            f"({', '.join(outputs[:8])}{'…' if len(outputs) > 8 else ''}) "
            f"via the module's routes/services."
        ),
        "output_where": where,
        "output_why": (
            f"Serves the {humanize(mod)} functions declared in its "
            f"FunctionGroupContracts."
        ),
        "process_description": " ".join(
            g.description.strip() for g in groups if g.description
        ),
        "process_context": (
            f"Derived record. Invoked via the {mod} module's registered "
            f"routes and dependencies."
        ),
        "narrative_events": [],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true", help="write files (default: dry run)")
    ap.add_argument("--dry-run", action="store_true", help="report only (default)")
    ap.add_argument("--only", nargs="*", default=None, help="limit to module dirs")
    args = ap.parse_args()

    from app.core.contract_loader import load_all_contracts
    from app.core.module_contracts import contract_registry
    from app.core.module_contract import ModuleContract

    load_all_contracts()
    by_module: dict[str, list] = {}
    for c in contract_registry.list_contracts():
        by_module.setdefault(c.module, []).append(c)

    written, skipped, would_write = [], [], []
    for module_dir in sorted(MODULES_DIR.iterdir()):
        if not module_dir.is_dir():
            continue
        mod = module_dir.name
        if args.only and mod not in args.only:
            continue
        # NO-TOUCH module — never write into onboarding without Brad's OK.
        if mod == "onboarding":
            skipped.append((mod, "NO-TOUCH module — excluded"))
            continue
        if (module_dir / "module_contract.json").exists():
            skipped.append((mod, "module_contract.json exists"))
            continue
        groups = by_module.get(mod)
        if not groups:
            skipped.append((mod, "no FunctionGroupContracts"))
            continue

        data = derive(module_dir, groups)
        # Validate against the real schema before offering to write.
        try:
            ModuleContract.model_validate(data)
        except Exception as exc:
            skipped.append((mod, f"derived contract fails schema: {exc}"))
            continue

        target = module_dir / "module_contract.json"
        if args.write:
            target.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            written.append(mod)
        else:
            would_write.append(mod)

    print(f"written: {len(written)}  would-write: {len(would_write)}  skipped: {len(skipped)}")
    for m in written:
        print(f"  WROTE  {m}")
    for m in would_write[:40]:
        print(f"  WOULD  {m}")
    if len(would_write) > 40:
        print(f"  … and {len(would_write) - 40} more")
    for m, why in skipped:
        print(f"  SKIP   {m}: {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
