"""
Regression test: no sync token refresh calls inside async routes.

Known Failure Registry #19: calling synchronous `get_valid_token_for_user()`
or `token_manager.get_valid_token()` from inside an `async def` route blocks
the uvicorn event loop and causes 504 / reconnect loops.

This test scans `app/` for `async def` functions and fails if any of them
still call the sync token helpers. Async routes must use:
  - `await app.core.auto_refresh.ensure_valid_token()`
  - `await app.core.auto_refresh.get_valid_token_or_redirect()`
  - `await app.core.oauth_token_manager.aget_valid_token_for_user()`
"""

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
APP_DIR = PROJECT_ROOT / "app"


# Sync calls that must not appear inside an async def body.
FORBIDDEN_SYNC_CALLS = [
    "get_valid_token_for_user(",
    "token_manager.get_valid_token(",
    "token_manager.validate_token(",
    "token_manager.refresh_token_if_needed(",
]

# Async equivalents that are allowed.
ALLOWED_ASYNC_PATTERNS = [
    "ensure_valid_token(",
    "get_valid_token_or_redirect(",
    "aget_valid_token_for_user(",
    "token_manager.aget_valid_token(",
    "token_manager.avalidate_token(",
    "token_manager.arefresh_token_if_needed(",
]

# Files where the sync helper is defined (allowed) or sync context only.
EXEMPT_FILES = {
    "app/core/oauth_token_manager.py",  # sync helpers defined here
    "app/core/auto_refresh.py",  # async only
    "app/core/storage_middleware.py",  # middleware, handled separately
}


def _function_bodies(content: str) -> list[tuple[int, str]]:
    """Extract (start_line, body_text) for each async def in a file."""
    results: list[tuple[int, str]] = []
    pattern = re.compile(r"^\s*async\s+def\s+\w+", re.MULTILINE)

    for match in pattern.finditer(content):
        # Find the end of this function (next top-level def/class at same or lower indent)
        start = match.start()
        start_line = content[:start].count("\n") + 1

        # Determine the indentation of the async def line
        line_start = content.rfind("\n", 0, start) + 1
        line_end = content.find("\n", start)
        if line_end == -1:
            line_end = len(content)
        indent = len(content[line_start:match.start()]) - len(
            content[line_start:match.start()].lstrip()
        )
        body_indent = indent + 4

        # Find the end of the function body
        pos = line_end
        while pos < len(content):
            next_newline = content.find("\n", pos)
            if next_newline == -1:
                next_newline = len(content)

            line = content[pos:next_newline]

            # If we hit a top-level construct at the original indent or lower, stop
            stripped = line.lstrip()
            if stripped and not stripped.startswith("#"):
                current_indent = len(line) - len(stripped)
                if current_indent <= indent and (
                    stripped.startswith("def ")
                    or stripped.startswith("async def ")
                    or stripped.startswith("class ")
                ):
                    break

            pos = next_newline + 1

        body = content[start:pos]
        results.append((start_line, body))

    return results


def test_no_sync_token_calls_in_async_routes():
    """Scan app/ for async def functions that call sync token helpers."""
    violations: list[str] = []

    for file_path in APP_DIR.rglob("*.py"):
        relative_path = str(file_path.relative_to(PROJECT_ROOT)).replace("\\", "/")

        if relative_path in EXEMPT_FILES:
            continue

        content = file_path.read_text(encoding="utf-8")

        for start_line, body in _function_bodies(content):
            for forbidden in FORBIDDEN_SYNC_CALLS:
                if forbidden in body:
                    # Make sure it's not just a reference inside a comment or string
                    for match in re.finditer(re.escape(forbidden), body):
                        line_num = body[: match.start()].count("\n") + start_line
                        violations.append(
                            f"{relative_path}:{line_num} - async def calls sync token helper: {forbidden}"
                        )

    if violations:
        msg = "Sync token helpers called from async def routes:\n" + "\n".join(violations)
        msg += "\n\nUse app.core.auto_refresh.ensure_valid_token() or aget_valid_token_for_user() instead."
        pytest.fail(msg)
