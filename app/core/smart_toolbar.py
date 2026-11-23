"""
Smart Toolbar — state-driven action projection
================================================

Given an entity's current state and a per-state rule map, project exactly
which actions render — and in what role:

- one PRIMARY action (the next real step — rendered ``.btn--primary``)
- up to ``max_visible`` CONTEXTUAL actions inline (``.btn--ghost`` /
  ``.btn--danger``)
- the remainder behind the template's native ``<details>`` overflow menu

Actions that are not valid in the current state are never rendered — this
repo does not show disabled buttons. See
``.devin/rules/12-state-driven-actions.md``.

This is the deterministic floor — what *can* be done here, right now. It
complements, and does not replace, ``action_router`` (AI-ranked
suggestions) and ``next_step_path`` (chronological path UI).

Usage
-----
Actions are ``app.core.action_maps.QuickAction`` entries — or any mapping /
object exposing ``action_id`` (or ``id``), ``label``, ``target`` (or
``endpoint``), ``action_type``, ``confirmation_prompt`` (or ``confirm``),
and ``danger``. Rules map a state name to a ``StateRule``::

    DOCUMENT_RULES = {
        "DRAFT":   StateRule(primary="submit", contextual=("edit", "delete")),
        "PENDING": StateRule(primary="download", contextual=("share",)),
        "FILED":   StateRule(contextual=("download", "share")),
    }

In the route::

    return templates.TemplateResponse(
        "doc_detail.html",
        {
            "request": request,
            "doc": doc,
            "toolbar": project_toolbar(
                doc.status,
                actions=DOCUMENT_ACTIONS,
                rules=DOCUMENT_RULES,
                resolve=resolve_action_url,
            ),
        },
    )

``resolve`` is a callable ``action -> url`` that goes through the
navigation registry / module contract — URL strings are never hardcoded
here (.devin/rules/03-ssot-redirects.md). When ``resolve`` is omitted the
action's ``endpoint``/``target`` field is used verbatim, which is fine for
actions whose target is already a concrete path.

Rendered by ``app/templates/components/smart_toolbar.html``, which expects::

    {"primary": entry|None, "visible": [entry, ...], "overflow": [entry, ...]}
    entry = {"id", "label", "endpoint", "method", "confirm", "danger"}
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

# Action types that render as plain links (GET). Anything else posts a form.
_LINK_TYPES = {"navigate", "download", "share", "external"}


@dataclass(frozen=True)
class StateRule:
    """Which actions are valid in one state, and which is the next step."""

    primary: str | None = None  # action_id promoted to the one main CTA
    contextual: tuple[str, ...] = ()  # ordered; first `max_visible` inline


def _field(action: Any, key: str, default: Any = None) -> Any:
    if isinstance(action, Mapping):
        return action.get(key, default)
    return getattr(action, key, default)


def _action_type(action: Any) -> str:
    raw = _field(action, "action_type", "") or ""
    return str(raw).rsplit(".", 1)[-1].lower()


def _entry(action: Any, resolve: Callable[[Any], str] | None) -> dict[str, Any]:
    return {
        "id": _field(action, "action_id") or _field(action, "id"),
        "label": _field(action, "label", ""),
        "endpoint": (
            resolve(action)
            if resolve
            else (_field(action, "endpoint") or _field(action, "target") or "#")
        ),
        "method": _field(action, "method")
        or ("GET" if _action_type(action) in _LINK_TYPES else "POST"),
        "confirm": _field(action, "confirmation_prompt") or _field(action, "confirm"),
        "danger": bool(_field(action, "danger", False)),
    }


def project_toolbar(
    state: str,
    *,
    actions: Mapping[str, Any],
    rules: Mapping[str, StateRule],
    max_visible: int = 3,
    resolve: Callable[[Any], str] | None = None,
) -> dict[str, Any]:
    """Project the toolbar contract for ``components/smart_toolbar.html``.

    ``rules`` maps state names (matched case-insensitively) to ``StateRule``.
    A state missing from ``rules`` projects an empty toolbar — nothing
    renders. Rule entries naming an action absent from ``actions`` are
    skipped silently: fewer buttons is a safe failure, a broken button is
    not.
    """
    rule = (
        rules.get(state)
        or rules.get(str(state).upper())
        or rules.get(str(state).lower())
    )
    if rule is None:
        return {"primary": None, "visible": [], "overflow": []}

    def entry(key: str | None) -> dict[str, Any] | None:
        action = actions.get(key) if key else None
        return _entry(action, resolve) if action is not None else None

    contextual = [e for key in rule.contextual if (e := entry(key)) is not None]
    return {
        "primary": entry(rule.primary),
        "visible": contextual[:max_visible],
        "overflow": contextual[max_visible:],
    }
