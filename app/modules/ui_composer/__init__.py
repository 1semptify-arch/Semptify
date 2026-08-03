"""UI Composer module — self-assembling tenant GUI.

The UI Composer is the "head waiter" of the tenant GUI. It decides WHAT to show
based on user context (from the Context Loop) and available modules (from the
Module Resolver), then assembles a page from the component library.

Architecture:
    User visits /tenant
        │
        ▸
    [Context Loop]          — get user state (intensity, documents, predicted_needs)
    [Module Resolver]       — what modules can this user see?
    [UI Composer]           — decide WHAT to show based on context + resolved modules
        │                     outputs: {page_title, pillar, components: [...]}
        ▸
    [Generic Template]      — render the component list
    [Component Library]     — each component is a Jinja macro

Page intents (initial set):
    - landing     — new/returning user landing page
    - timeline    — RECORD pillar home (merged feed)
    - library     — KNOW pillar (subject grid + facts)
    - documents   — document vault
    - tools       — deadline tracker + letter generators
    - workflow_step — single workflow step view
"""

from .router import router

__all__ = ["router"]
