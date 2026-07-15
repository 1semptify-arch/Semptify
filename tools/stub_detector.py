#!/usr/bin/env python3
"""
stub_detector.py

Scans a Python codebase for genuine stubs -- functions/methods whose body is
still a placeholder (pass, ..., raise NotImplementedError, or a bare
return of an empty literal) -- and writes them out as tasks, in the same
shape your agent_orchestrator_tasks.json already uses.

Why this version instead of a keyword search:
Keyword search (grepping for "TODO", "placeholder", "stub", etc.) matches
the WORD wherever it appears -- in HTML attributes, CSS properties, FastAPI
Depends() defaults, docstrings, comments describing a future feature, and
so on. That's exactly what produced the 123 false positives.

This version instead parses the actual Python syntax tree (ast module) and
only flags a function/method if its *body* -- the real executable code --
is empty or a placeholder. It doesn't care what words appear near it.

Built-in fixes (per the false-positive categories found):
  1. Only .py files are ever scanned -- HTML/CSS/JS are skipped entirely
     by extension, so "coming soon" badges, CSS `content:` rules, and
     `placeholder="..."` form attributes can never match.
  2. Any path containing a `_template` (or `templates_scaffold`) directory
     is skipped -- those are intentional scaffolds.
  3. A `# TODO` / `# FIXME` comment on its own is informational, not a
     stub -- comments are never treated as code needing a task. (If you
     want a *separate* list of documented-TODO comments, use --list-todos;
     they're reported but never turned into stub_fix tasks.)
  4. `return []` / `return {}` / `return None` inside an `except` block is
     recognized as defensive/fallback code, not a stub, and is skipped --
     unless it's the ENTIRE function body with no other statements in the
     try block either (a function that is 100% just "except: return {}"
     with nothing else going on is still flagged).
  5. Every flag is a real AST node (ast.Pass, ast.Ellipsis constant,
     ast.Raise with NotImplementedError, or a lone ast.Return of an empty
     literal) -- never a text/regex match -- so there's nothing to
     "verify the line actually matches the pattern" for; the parser
     already guarantees it.

Usage:
    python stub_detector.py <root_dir> [--out stub_tasks.json] [--list-todos]

Output: a JSON list of task dicts:
    {
      "id": 1,
      "category": "stub_fix",
      "file": "app/modules/foo/router.py",
      "line": 42,
      "function": "get_widget",
      "reason": "raise NotImplementedError",
      "status": "pending"
    }
"""

import argparse
import ast
import json
import sys
from pathlib import Path

SKIP_DIR_NAMES = {
    # Scaffolds
    "_template", "templates_scaffold",
    # Virtual envs (also caught by prefix check below, but listed for clarity)
    "venv", "venv311", "venv311_clean", ".venv", "env",
    # Caches / build artifacts
    "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache",
    ".pre-commit", "dist", "build", "htmlcov", "test-results",
    "node_modules", ".git",
    # Non-app directories with third-party / generated / unrelated Python
    "archive", "logs", "uploads", "REPOs", "bsimpotrrttd",
    "installer", "mobile_ai_host", "semptify_dakota_eviction",
    "legal_intel",
    # Agent / tooling work directories
    ".agent", ".agent-mem", ".agents", ".semptify",
    ".zenflow", ".zencoder", ".windsurf", ".cursor", ".devin",
    ".github", ".vscode",
}

SKIP_DIR_PREFIXES = ("venv", ".venv", "env")

# Alembic merge migrations have empty upgrade()/downgrade() bodies by design.
# This is the correct pattern for merge revisions — they exist only to merge
# multiple alembic heads, not to apply schema changes. Skip them permanently.
ALEMBIC_SKIP_FN_NAMES = {"upgrade", "downgrade"}

STUB_REASONS = {
    "pass": "function body is only `pass`",
    "ellipsis": "function body is only `...`",
    "not_implemented": "raises NotImplementedError",
    "empty_return": "function body is only a bare return of an empty literal",
}


def is_abstract_method(node) -> bool:
    """Return True if a function/method is decorated with @abstractmethod."""
    for decorator in getattr(node, "decorator_list", []):
        if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
            return True
        if isinstance(decorator, ast.Attribute) and decorator.attr == "abstractmethod":
            return True
        if isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Name) and func.id == "abstractmethod":
                return True
            if isinstance(func, ast.Attribute) and func.attr == "abstractmethod":
                return True
    return False


def _type_names(node):
    """Collect bare names appearing in an except handler type expression."""
    names = set()
    if node is None:
        return names
    if isinstance(node, ast.Name):
        names.add(node.id)
    elif isinstance(node, ast.Tuple):
        for elt in node.elts:
            names.update(_type_names(elt))
    elif isinstance(node, ast.Attribute):
        names.add(node.attr)
    return names


IMPORT_ERROR_NAMES = {"ImportError", "ModuleNotFoundError"}


def is_skipped_path(path: Path) -> bool:
    for part in path.parts:
        if part in SKIP_DIR_NAMES:
            return True
        # Catch any venvXXX, .venvXXX, envXXX directories by prefix
        for prefix in SKIP_DIR_PREFIXES:
            if part.startswith(prefix) and part != prefix:
                # Only skip if it's a venv-style name (avoid skipping e.g. "env_vars")
                rest = part[len(prefix):]
                if rest == "" or rest[0] in "_-." or rest.isdigit():
                    return True
    return False


def body_is_stub(body):
    """
    Given a function's list of AST statements, return a reason string if it's
    a genuine stub, else None.

    A docstring-only prefix is allowed and ignored (very common, not a stub
    signal by itself).
    """
    stmts = list(body)
    # Drop a leading docstring expression, if present.
    if stmts and isinstance(stmts[0], ast.Expr) and isinstance(
        getattr(stmts[0], "value", None), (ast.Constant,)
    ) and isinstance(stmts[0].value.value, str):
        stmts = stmts[1:]

    if not stmts:
        return None  # nothing left to judge (shouldn't happen for valid code)

    if len(stmts) == 1:
        stmt = stmts[0]

        # A function whose ENTIRE body is a single try/except, where the try
        # side does nothing real and every handler just returns an empty
        # literal, is still a stub in disguise.
        if isinstance(stmt, ast.Try):
            try_body = stmt.body
            try_trivial = len(try_body) == 1 and isinstance(try_body[0], (ast.Pass,))
            if try_trivial and stmt.handlers:
                all_handlers_empty = True
                for handler in stmt.handlers:
                    hbody = handler.body
                    if len(hbody) != 1 or not isinstance(hbody[0], ast.Return):
                        all_handlers_empty = False
                        break
                    val = hbody[0].value
                    is_empty = (
                        val is None
                        or (isinstance(val, ast.Constant) and val.value is None)
                        or (isinstance(val, (ast.List, ast.Dict, ast.Tuple, ast.Set))
                            and not (val.elts if hasattr(val, "elts") else getattr(val, "keys", [])))
                    )
                    if not is_empty:
                        all_handlers_empty = False
                        break
                if all_handlers_empty:
                    return "function body is only a trivial try/except that returns an empty value"
            return None

        if isinstance(stmt, ast.Pass):
            return STUB_REASONS["pass"]

        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) \
                and stmt.value.value is Ellipsis:
            return STUB_REASONS["ellipsis"]

        if isinstance(stmt, ast.Raise):
            exc = stmt.exc
            name = None
            if isinstance(exc, ast.Call):
                name = getattr(exc.func, "id", None)
            elif isinstance(exc, ast.Name):
                name = exc.id
            if name == "NotImplementedError":
                return STUB_REASONS["not_implemented"]

        if isinstance(stmt, ast.Return):
            val = stmt.value
            if val is None:
                return None  # bare `return` alone isn't necessarily a stub
            if isinstance(val, ast.Constant) and val.value is None:
                return STUB_REASONS["empty_return"]
            if isinstance(val, (ast.List, ast.Dict, ast.Tuple, ast.Set)) and not (
                val.elts if hasattr(val, "elts") else getattr(val, "keys", [])
            ):
                return STUB_REASONS["empty_return"]

    return None


def find_enclosing_except(node, tree):
    """
    Return True if `node` sits directly inside an `except` handler's body
    (used to allow a lone `return []`/`{}`/`None` there as legitimate
    fallback code rather than a stub) -- UNLESS the function has no other
    real logic at all (i.e. the whole function is just a bare except).
    """
    for parent in ast.walk(tree):
        if isinstance(parent, ast.Try):
            for handler in parent.handlers:
                if node in ast.walk(handler):
                    return True
    return False


IGNORE_PRAGMA = "# stub-detector: ignore"


class StubVisitor(ast.NodeVisitor):
    def __init__(self, filename, tree, source_lines):
        self.filename = filename
        self.tree = tree
        self.source_lines = source_lines
        self.findings = []
        self._in_import_error_handler = 0

    def _is_ignored(self, node):
        """Check the line immediately above the function definition for an ignore pragma."""
        if not self.source_lines or node.lineno < 2:
            return False
        prev_line = self.source_lines[node.lineno - 2]
        return IGNORE_PRAGMA in prev_line

    def _check(self, node):
        # Abstract base class methods are intentionally empty.
        if is_abstract_method(node):
            return

        # Functions defined inside an `except ImportError:` block are fallback
        # shims for optional dependencies, not stubs to fix.
        if self._in_import_error_handler > 0:
            return

        # Allow an explicit pragma to mark an intentionally empty helper.
        if self._is_ignored(node):
            return

        reason = body_is_stub(node.body)
        if reason is None:
            return

        # Alembic merge migrations have empty upgrade()/downgrade() bodies
        # by design — this is the correct pattern, not a stub.
        if (
            node.name in ALEMBIC_SKIP_FN_NAMES
            and ("alembic" in self.filename and "versions" in self.filename)
        ):
            return

        # If the stub-triggering statement is itself inside an except block,
        # and the function has other real statements outside that block,
        # treat it as legitimate defensive code -- not a stub.
        if reason == STUB_REASONS["empty_return"]:
            last_stmt = node.body[-1]
            if find_enclosing_except(last_stmt, node) and len(node.body) > 1:
                return

        self.findings.append({
            "file": self.filename,
            "line": node.lineno,
            "function": node.name,
            "reason": reason,
        })

    def visit_ExceptHandler(self, node):
        handler_names = _type_names(node.type)
        is_import_error = bool(handler_names & IMPORT_ERROR_NAMES)
        if is_import_error:
            self._in_import_error_handler += 1
        self.generic_visit(node)
        if is_import_error:
            self._in_import_error_handler -= 1

    def visit_FunctionDef(self, node):
        self._check(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self._check(node)
        self.generic_visit(node)


def scan_file(path: Path, root: Path, list_todos=False):
    try:
        source = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return [], []

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return [], []

    visitor = StubVisitor(str(path.relative_to(root)), tree, source.splitlines())
    visitor.visit(tree)

    todos = []
    if list_todos:
        for i, line in enumerate(source.splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("#") and ("TODO" in stripped or "FIXME" in stripped):
                todos.append({
                    "file": str(path.relative_to(root)),
                    "line": i,
                    "text": stripped.lstrip("#").strip(),
                })

    return visitor.findings, todos


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", default=".", help="Root directory to scan (default: current working directory)")
    ap.add_argument("--out", default="stub_tasks.json", help="Output JSON path")
    ap.add_argument("--list-todos", action="store_true",
                     help="Also write todo_comments.json listing documented TODO/FIXME comments (informational only, never turned into tasks)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root not found: {root}", file=sys.stderr)
        sys.exit(1)

    all_findings = []
    all_todos = []

    for path in root.rglob("*.py"):
        if is_skipped_path(path.relative_to(root)):
            continue
        findings, todos = scan_file(path, root, list_todos=args.list_todos)
        all_findings.extend(findings)
        all_todos.extend(todos)

    tasks = []
    for i, f in enumerate(all_findings, start=1):
        tasks.append({
            "id": i,
            "category": "stub_fix",
            "file": f["file"],
            "line": f["line"],
            "function": f["function"],
            "reason": f["reason"],
            "status": "pending",
        })

    Path(args.out).write_text(json.dumps(tasks, indent=2), encoding="utf-8")
    print(f"Found {len(tasks)} real stub(s). Wrote {args.out}")
    for t in tasks:
        print(f"  {t['file']}:{t['line']}  {t['function']}()  -- {t['reason']}")

    if args.list_todos:
        todo_path = Path("todo_comments.json")
        todo_path.write_text(json.dumps(all_todos, indent=2), encoding="utf-8")
        print(f"\nAlso found {len(all_todos)} documented TODO/FIXME comment(s) "
              f"(informational only -- see {todo_path}). These are NOT tasks.")

    return len(tasks)


if __name__ == "__main__":
    sys.exit(0 if main() == 0 else 1)
