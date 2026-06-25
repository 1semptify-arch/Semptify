"""Page Composer module — assembles Context Engine facts + stories + case data.

Composes a unified page view for a given subject + jurisdiction so frontend
pages can render verified facts, relevant tenant stories, and the user's own
case data in one call. Replaces scattered frontend fetches with one bundle.

Design:
- One endpoint: GET /api/page/{subject}
- Pulls facts + stories from Context Engine (cited, no hallucination)
- Pulls user's case data from case_builder if available
- All sections optional — returns what exists
- Calm tone, jurisdiction-aware
"""

from .router import router

__all__ = ["router"]
