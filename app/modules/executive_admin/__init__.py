"""Executive Administration — Semptify's own nonprofit back office.

MN + federal 501(c)(3) formation roadmap, compliance calendar, board and
meetings, policies, the books of record (990 classes, restricted funds,
donor receipts), and grant readiness. Org-level data only — never tenant
data. Admin-elevation gated; mounted at /admin/executive.
"""

from app.modules.executive_admin.router import router

__all__ = ["router"]
