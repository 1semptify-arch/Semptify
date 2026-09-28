"""Case File Review & Evidence Index module.

Per-case document categorization and cross-document evidence index for
attorney/legal-reviewer sessions. All records persist as EVIDENCE_INDEX
overlays in the tenant's own cloud vault — zero Semptify-side persistence,
original documents are immutable and never written by this module.
"""

from app.modules.case_review import router  # noqa: F401
