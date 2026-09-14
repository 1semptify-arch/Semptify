"""Eviction Timeline module — chronological case-event tracking.

Tenant-facing, T2 data. ``subject_id`` is a nullable FK to
``accountability_subjects`` (the accountability ledger) — set when the
event can be attributed to a known subject.
"""

from .router import router

__all__ = ["router"]
