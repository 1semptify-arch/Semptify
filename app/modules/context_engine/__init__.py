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


def __getattr__(name: str):
    # Lazy router export: importing app.modules.context_engine.models (pulled
    # by app.models.models, which app.core.security needs at app import time)
    # must not drag in the full router/retrieval/embedding chain — that cost
    # is what pushed Render cold-boot past the port-scan window.
    if name == "router":
        from .router import router

        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["router"]
