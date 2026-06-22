"""Context Engine module — verified facts + tenant stories for housing-rights context.

Surfaces relevant facts and stories to users based on their current task.
All facts are cited (no hallucination). Stories surface after task completion
and are saved to the user's journal.

Design pillars:
- No hallucination: every fact has a source URL
- No legal advice: informational only
- Stories anonymized + moderated
- Calm tone, jurisdiction-aware
- `avoided_court` is the hero frame, not "I won"
"""

from .router import router

__all__ = ["router"]
