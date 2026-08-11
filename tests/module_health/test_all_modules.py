"""Consolidated module health regression tests.

Replaces the 122 individual ``test_<id>.py`` stub files with a single
parametrized test that iterates every module in ``tools/module_registry.yaml``
and calls the corresponding ``check_<id>()`` function from
``tools.module_health``.

Each module gets its own test case ID so failures are easy to identify:

    pytest tests/module_health/test_all_modules.py -k auth
"""

from __future__ import annotations

import re

import pytest

from tools.module_health import _load_registry

# Build the parametrized list once at import time.
# Each entry yields (module_id, check_function) pairs.
_REGISTRY = _load_registry()
_PARAMS = []
for _entry in _REGISTRY:
    _id = _entry.get("id")
    _path = _entry.get("module_path")
    if not _id or not _path:
        continue
    # Skip entries that are flagged (ON HOLD, optional, pending decision, etc.)
    # — these were never given individual test files by generate_module_health.py.
    if _entry.get("flag_reason") or _entry.get("health_check") in ("TODO", "", None):
        continue
    _safe = re.sub(r"[^a-z0-9_]", "_", _id).lower()
    _check_name = f"check_{_safe}"
    # Import the dynamically-generated check function.
    import tools.module_health as _mh

    _check = getattr(_mh, _check_name, None)
    if _check is not None:
        _PARAMS.append(pytest.param(_check, id=_id))


@pytest.mark.module_health
@pytest.mark.parametrize("check_fn", _PARAMS)
def test_module_health(check_fn):
    """Verify every registered module imports, has routes, and has no exposure issues."""
    ok, msg = check_fn()
    assert ok, msg
