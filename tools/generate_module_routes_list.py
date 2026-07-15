"""
Regenerate module_routes_list.txt from app/modules/*/router.py files.

Counts HTTP route decorators on any APIRouter variable (not just `router`).
This prevents false duplicate tasks caused by stale route counts.
"""
import ast
import re
from pathlib import Path

MODULES_DIR = Path(__file__).parent.parent / "app" / "modules"
OUT_FILE = Path(__file__).parent.parent / "module_routes_list.txt"

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head", "trace"}


def find_router_vars(tree: ast.Module) -> set[str]:
    """Find variable names assigned an APIRouter(...) call."""
    router_vars = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            value = node.value
            if isinstance(value, ast.Call):
                func = value.func
                if isinstance(func, ast.Name) and func.id == "APIRouter":
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            router_vars.add(target.id)
                elif isinstance(func, ast.Attribute) and func.attr == "APIRouter":
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            router_vars.add(target.id)
    return router_vars


def generate() -> None:
    sections: list[str] = []
    module_dirs = sorted(p for p in MODULES_DIR.iterdir() if p.is_dir() and not p.name.startswith("_"))

    for module_dir in module_dirs:
        router_file = module_dir / "router.py"
        if not router_file.exists():
            continue

        source = router_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            sections.append(f"=== {module_dir.name} (parse error) ===\n")
            continue

        router_vars = find_router_vars(tree)
        if not router_vars:
            sections.append(f"=== {module_dir.name} (0 routes) ===\n")
            continue

        # Find decorator source lines that belong to one of the routers.
        pattern = re.compile(r"^\s*@(" + "|".join(re.escape(v) for v in router_vars) + r")\.(" + "|".join(HTTP_METHODS) + r")\(")
        route_lines: list[str] = []
        for raw_line in source.splitlines():
            if pattern.search(raw_line):
                route_lines.append("  " + raw_line.strip())

        count = len(route_lines)
        sections.append(f"=== {module_dir.name} ({count} routes) ===\n")
        if route_lines:
            sections.extend(line + "\n" for line in route_lines)

    OUT_FILE.write_text("".join(sections), encoding="utf-8")
    print(f"Wrote {OUT_FILE} with {len(sections)} sections.")


if __name__ == "__main__":
    generate()
