"""Page Composer module — assembles Context Engine facts + stories + case data.

Provides:
- Legacy compose: GET /api/page/{subject}
- New assembly formula: GET /api/page/{subject}/assemble
"""

from .router import router

__all__ = ["router"]
