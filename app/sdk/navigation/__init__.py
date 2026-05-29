"""
Semptify Navigation SDK
========================
Framework-free navigation primitives.

Thin wrapper over app.core.navigation — the SSOT for all paths.
Any module can import from here without coupling to FastAPI.

Usage:
    from app.sdk.navigation import get_stage, get_path, get_onboarding_start

    path = get_path("preamble")          # "/preamble"
    start = get_onboarding_start()       # "/preamble"
    next_p = get_next_path("providers")  # "/onboarding/vault-setup" etc.
"""

from app.sdk.navigation.client import (
    get_stage,
    get_path,
    get_onboarding_start,
    get_reconnect_path,
    get_next_path,
    is_canonical_path,
    all_paths,
)

__all__ = [
    "get_stage",
    "get_path",
    "get_onboarding_start",
    "get_reconnect_path",
    "get_next_path",
    "is_canonical_path",
    "all_paths",
]
