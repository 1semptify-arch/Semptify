"""Eviction Timeline module — chronological case-event tracking.

Tenant-facing, T2 data. `subject_id` is a placeholder only; the
accountability_ledger boundary is intentionally deferred.
"""

from .router import router

__all__ = ["router"]
