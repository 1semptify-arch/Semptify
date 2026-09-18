"""DEPRECATED shim — canonical implementation lives in app.modules.mndes.service.

This module previously held a near-duplicate copy of the MNDES exhibit service
that drifted out of sync with the live implementation (the router imports
`app.modules.mndes.service`). Kept as a re-export so legacy import paths and
tests keep resolving to the single canonical implementation.
"""

from app.modules.mndes.service import MNDESExhibitService, mndes_exhibit_service

__all__ = ["MNDESExhibitService", "mndes_exhibit_service"]
