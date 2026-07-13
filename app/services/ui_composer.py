"""UI Composer service — decides WHAT to show based on user context.

This is the "head waiter" of the tenant GUI. It reads user state from the
Context Loop and available modules from the Module Resolver, then assembles
a page as a list of components.

Output contract (registered in module_contracts.py):
    compose_page(user_id, page_intent, context?) -> {
        "page_title": str,
        "pillar": "RECORD" | "KNOW" | None,
        "components": [{"type": str, "data": dict}, ...]
    }

Component types (initial set):
    - welcome_message
    - settings_prompt
    - document_review_prompt
    - fact_card
    - timeline_event
    - timeline_group
    - filter_chips
    - subject_grid
    - add_record_button
    - add_record_modal
    - process_indicator
    - prompt_card
    - stat_badge
    - empty_state

No hallucination: every component type is listed in COMPONENT_TYPES below.
If a caller asks for an unknown component type, compose_page raises ValueError.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _modal_data() -> Dict[str, Any]:
    """Shared data for the Add Record modal (pre-fills today's date)."""
    return {"today": date.today().isoformat()}


# --- Component type registry (SSOT for valid component types) ----------
COMPONENT_TYPES = {
    "welcome_message",
    "settings_prompt",
    "document_review_prompt",
    "fact_card",
    "timeline_event",
    "timeline_group",
    "filter_chips",
    "subject_grid",
    "add_record_button",
    "add_record_modal",
    "process_indicator",
    "prompt_card",
    "stat_badge",
    "empty_state",
}

# --- Page intent registry (SSOT for valid page intents) ----------------
PAGE_INTENTS = {
    "landing",
    "timeline",
    "library",
    "documents",
    "tools",
    "workflow_step",
}

# Pillar labels
PILLAR_RECORD = "RECORD"
PILLAR_KNOW = "KNOW"


def _component(ctype: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build a component dict. Validates type against COMPONENT_TYPES."""
    if ctype not in COMPONENT_TYPES:
        raise ValueError(f"Unknown component type: {ctype}. Valid: {sorted(COMPONENT_TYPES)}")
    return {"type": ctype, "data": data or {}}


def _get_user_context(user_id: str) -> Dict[str, Any]:
    """Get user context from the Context Loop.

    Falls back to empty context if Context Loop is unavailable — the UI Composer
    must never crash the page render. It degrades gracefully to an empty state.
    """
    try:
        from app.services.context_loop import context_loop
        ctx = context_loop.get_user_context(user_id) if hasattr(context_loop, "get_user_context") else {}
        if ctx is None:
            return {}
        return dict(ctx)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("UI Composer: Context Loop unavailable for %s: %s", user_id, e)
        return {}


def _get_resolved_modules(user_id: str, role: str = "tenant") -> List[str]:
    """Get the list of module paths the user can see.

    Falls back to empty list if Module Resolver is unavailable.
    """
    try:
        # Module Resolver is async — but we expose a sync wrapper for the composer.
        # The router's async endpoints can call the async resolver directly.
        # For the composer's sync use, we return empty and let the router enrich.
        return []
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("UI Composer: Module Resolver unavailable for %s: %s", user_id, e)
        return []


def _is_new_user(context: Dict[str, Any]) -> bool:
    """Heuristic: a user is 'new' if they have ≤1 document and no urgency."""
    doc_count = context.get("document_count", 0)
    intensity = context.get("intensity", 0)
    return doc_count <= 1 and intensity < 20


def compose_page(
    user_id: str,
    page_intent: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compose a page as a list of components.

    Args:
        user_id: The user's ID (for context lookup)
        page_intent: One of PAGE_INTENTS (e.g. "landing", "timeline", "library")
        context: Optional override context (skips Context Loop lookup if provided)

    Returns:
        {
            "page_title": str,
            "pillar": "RECORD" | "KNOW" | None,
            "components": [{"type": str, "data": dict}, ...],
        }

    Raises:
        ValueError: If page_intent is not in PAGE_INTENTS.
    """
    if page_intent not in PAGE_INTENTS:
        raise ValueError(
            f"Unknown page intent: {page_intent}. Valid: {sorted(PAGE_INTENTS)}"
        )

    # Get user context (from caller or Context Loop)
    ctx = context if context is not None else _get_user_context(user_id)

    # Dispatch to the right composer
    if page_intent == "landing":
        return _compose_landing(user_id, ctx)
    if page_intent == "timeline":
        return _compose_timeline(user_id, ctx)
    if page_intent == "library":
        return _compose_library(user_id, ctx)
    if page_intent == "documents":
        return _compose_documents(user_id, ctx)
    if page_intent == "tools":
        return _compose_tools(user_id, ctx)
    if page_intent == "workflow_step":
        return _compose_workflow_step(user_id, ctx)
    # Should never reach here due to validation above
    raise ValueError(f"Unhandled page intent: {page_intent}")


def _compose_landing(user_id: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Compose the landing page for a new or returning user.

    New user (≤1 doc, low intensity):
        welcome_message + settings_prompt + document_review_prompt + add_record_button

    Returning user:
        stat_badges + prompt_card + add_record_button
    """
    components: List[Dict[str, Any]] = []

    if _is_new_user(ctx):
        components.append(_component("welcome_message", {
            "user_name": ctx.get("user_name", ""),
            "doc_count": ctx.get("document_count", 0),
        }))
        components.append(_component("settings_prompt", {
            "has_settings": ctx.get("has_settings", False),
        }))
        components.append(_component("document_review_prompt", {
            "doc_count": ctx.get("document_count", 0),
        }))
    else:
        # Returning user — show stats and a prompt
        components.append(_component("stat_badge", {
            "label": "Documents",
            "value": ctx.get("document_count", 0),
            "icon": "📄",
        }))
        components.append(_component("stat_badge", {
            "label": "Upcoming deadlines",
            "value": ctx.get("upcoming_deadlines", 0),
            "icon": "⏰",
        }))
        components.append(_component("prompt_card", {
            "title": "Welcome back",
            "body": "Pick up where you left off, or add a new record.",
            "cta_label": "View timeline",
            "cta_path": "/tenant/timeline",
        }))

    components.append(_component("add_record_button"))
    components.append(_component("add_record_modal", _modal_data()))

    return {
        "page_title": "My Home — Semptify",
        "pillar": None,
        "components": components,
    }


def _compose_timeline(user_id: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Compose the RECORD pillar — timeline of everything.

    Components:
        filter_chips + timeline_group(s) + add_record_button + add_record_modal

    The actual feed data is fetched by the tenant_feed module (Phase 1B).
    For Phase 1A, we emit the structure with empty data — the router will
    enrich with real feed data when available.
    """
    components: List[Dict[str, Any]] = []

    # Stat badges in timeline header
    components.append(_component("stat_badge", {
        "label": "Documents",
        "value": ctx.get("document_count", 0),
        "icon": "📄",
    }))
    components.append(_component("stat_badge", {
        "label": "Upcoming deadlines",
        "value": ctx.get("upcoming_deadlines", 0),
        "icon": "⏰",
    }))

    # Filter chips (HTMX swaps the timeline_group below)
    components.append(_component("filter_chips", {
        "filters": [
            {"id": "all", "label": "All", "active": True},
            {"id": "documents", "label": "Documents"},
            {"id": "events", "label": "Events"},
            {"id": "journal", "label": "Journal"},
            {"id": "letters", "label": "Letters"},
            {"id": "deadlines", "label": "Deadlines"},
        ],
        "hx_target": "/api/ui/fragment/timeline_group",
    }))

    # Timeline group (placeholder — Phase 1B will feed real data)
    components.append(_component("timeline_group", {
        "date_label": "Today",
        "events": [],  # Filled by tenant_feed aggregator
        "empty": ctx.get("document_count", 0) == 0,
    }))

    components.append(_component("add_record_button"))
    components.append(_component("add_record_modal", _modal_data()))

    return {
        "page_title": "Timeline — Semptify",
        "pillar": PILLAR_RECORD,
        "components": components,
    }


def _compose_library(user_id: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Compose the KNOW pillar — library of verified facts.

    Components:
        subject_grid (13 subjects from the Context Engine taxonomy)
        fact_card list when a pre-selected subject is passed in ctx

    Clicking a subject triggers an HTMX swap to fact_card(s) + stories
    via /api/ui/fragment/library/{subject}.
    """
    from app.modules.context_engine.taxonomy import ALL_SUBJECTS, SUBJECT_LABELS

    # Icon map for the 13 canonical subjects — keeps the grid visual
    # without hardcoding labels (those come from SUBJECT_LABELS).
    _SUBJECT_ICONS = {
        "eviction": "🚪",
        "repair": "🔧",
        "rent": "💵",
        "lease": "📋",
        "deposit": "💰",
        "discrimination": "⚖️",
        "safety": "🛡️",
        "habitability": "🏠",
        "retaliation": "🛡️",
        "small_claims": "⚖️",
        "court_prep": "🏛️",
        "evidence": "📄",
        "timeline": "📅",
    }

    components: List[Dict[str, Any]] = []

    selected_subject = ctx.get("subject")
    if selected_subject and selected_subject in ALL_SUBJECTS:
        facts = ctx.get("facts") or []
        stories = ctx.get("stories") or []
        label = ctx.get("label") or SUBJECT_LABELS.get(selected_subject, selected_subject)

        if not facts and not stories:
            components.append(_component("empty_state", {
                "icon": "📚",
                "title": f"No verified facts yet for {label}",
                "body": "This topic has not been populated yet. Choose another topic or check back later.",
            }))
        else:
            story_texts = [
                {"text": s.get("title") or s.get("body") or ""}
                for s in stories
                if s.get("title") or s.get("body")
            ]
            for idx, fact in enumerate(facts):
                components.append(_component("fact_card", {
                    "title": fact.get("claim") or "Verified fact",
                    "body": fact.get("citation") or fact.get("body") or "",
                    "source_url": fact.get("source_url") or "",
                    "source_label": fact.get("source_name") or fact.get("source_url") or "",
                    "stories": story_texts if idx == 0 else [],
                }))

    # 13 subjects — the KNOW pillar root (from the canonical taxonomy)
    components.append(_component("subject_grid", {
        "subjects": [
            {
                "id": s,
                "label": SUBJECT_LABELS.get(s, s),
                "icon": _SUBJECT_ICONS.get(s, "•"),
            }
            for s in ALL_SUBJECTS
        ],
        "active_subject": selected_subject,
        "hx_target": "/api/ui/fragment/library/",
    }))

    components.append(_component("add_record_button"))
    components.append(_component("add_record_modal", _modal_data()))

    if selected_subject and selected_subject in ALL_SUBJECTS:
        label = SUBJECT_LABELS.get(selected_subject, selected_subject)
        page_title = f"{label} — Know Your Rights — Semptify"
    else:
        page_title = "Library — Know Your Rights — Semptify"

    return {
        "page_title": page_title,
        "pillar": PILLAR_KNOW,
        "components": components,
    }


def _compose_documents(user_id: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Compose the documents page — document vault grid."""
    components: List[Dict[str, Any]] = []

    components.append(_component("stat_badge", {
        "label": "Total documents",
        "value": ctx.get("document_count", 0),
        "icon": "📄",
    }))

    if ctx.get("document_count", 0) == 0:
        components.append(_component("empty_state", {
            "icon": "📄",
            "title": "No documents yet",
            "body": "Add your first document — lease, photos, receipts, communications.",
            "cta_label": "Add a document",
            "cta_path": "/tenant/documents",
        }))
    else:
        # The actual document list is rendered by the existing documents endpoint.
        # UI Composer emits a placeholder — the router can enrich with real data.
        components.append(_component("timeline_group", {
            "date_label": "Recent documents",
            "events": [],  # Filled by documents endpoint
            "empty": False,
        }))

    components.append(_component("add_record_button"))
    components.append(_component("add_record_modal", _modal_data()))

    return {
        "page_title": "Documents — Semptify",
        "pillar": PILLAR_RECORD,
        "components": components,
    }


def _compose_tools(user_id: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Compose the tools page — deadline tracker + letter generators."""
    components: List[Dict[str, Any]] = []

    components.append(_component("prompt_card", {
        "title": "Deadlines",
        "body": "Track important dates — court, lease end, repair deadlines.",
        "cta_label": "Open deadline tracker",
        "cta_path": "/tenant/tools/deadlines",
    }))
    components.append(_component("prompt_card", {
        "title": "Letters",
        "body": "Generate template letters — repair request, notice to vacate, etc.",
        "cta_label": "Open letter generator",
        "cta_path": "/tenant/tools/letters",
    }))

    components.append(_component("add_record_button"))
    components.append(_component("add_record_modal", _modal_data()))

    return {
        "page_title": "Tools — Semptify",
        "pillar": None,
        "components": components,
    }


def _compose_workflow_step(user_id: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Compose a single workflow step view with a process indicator."""
    components: List[Dict[str, Any]] = []

    workflow_id = ctx.get("workflow_id", "")
    step_label = ctx.get("step_label", "Working...")
    state = ctx.get("state", "running")
    progress = ctx.get("progress_pct", 0)

    components.append(_component("process_indicator", {
        "workflow_id": workflow_id,
        "step_label": step_label,
        "state": state,  # pending | running | complete | error
        "progress_pct": progress,
    }))

    return {
        "page_title": "Processing — Semptify",
        "pillar": None,
        "components": components,
    }


def render_fragment(component_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Render a single component as a fragment (for HTMX swaps).

    Returns the component dict — the router will render it via Jinja.

    Args:
        component_type: One of COMPONENT_TYPES
        data: Component data

    Returns:
        {"type": str, "data": dict}

    Raises:
        ValueError: If component_type is not in COMPONENT_TYPES.
    """
    return _component(component_type, data)


def get_process_status(workflow_id: str) -> Dict[str, Any]:
    """Get the current status of a workflow for the process indicator.

    Reads from the Positronic Mesh if available. Falls back to a
    "running" state with a generic label if unavailable.

    Args:
        workflow_id: The workflow ID from the Positronic Mesh

    Returns:
        {"step_label": str, "state": str, "progress_pct": int}
    """
    try:
        from app.core.positronic_mesh import positronic_mesh
        status = positronic_mesh.get_workflow_status(workflow_id)
        if status:
            return {
                "step_label": status.get("step_label", "Working..."),
                "state": status.get("state", "running"),
                "progress_pct": status.get("progress_pct", 0),
            }
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("UI Composer: Positronic Mesh unavailable for %s: %s", workflow_id, e)

    # Fallback — generic running state
    return {
        "step_label": "Working...",
        "state": "running",
        "progress_pct": 0,
    }
