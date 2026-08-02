"""Page Composer module — assembles Context Engine facts + stories + case data.

Provides:
- Legacy compose: GET /api/page/{subject}
- New assembly formula: GET /api/page/{subject}/assemble
- Page Shell rendering: GET /api/page/{subject}/render
"""

from .router import router

__all__ = ["router"]
