"""Real-Time Narrator — contract-driven narration renderer (ADR-0008 §2.3,
SEMPTIFY_BUILD_CONTRACT Part 2).

Sentence grammar (approved Part 2): [Actor] [Verb] [Object] [Context clause].

A module emits narration by publishing a real backend event whose ``data``
carries a narrator slot reference::

    data["narrator"] = {"module": "app.modules.document_center", "slot": 0}

The WebSocket boundary (:meth:`EventBus._push_to_websockets`) resolves that
reference against the module's ``module_contract.json`` and injects the
rendered sentence. Narration text always comes from the approved contract
file — never a freeform string in the publish call — so a line can only
describe a step the module declared and actually ran.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.module_contract import ModuleContractRegistry, NarratorEvent

logger = logging.getLogger(__name__)

# Key an event's ``data`` carries to request contract-driven narration.
NARRATOR_DATA_KEY = "narrator"

_registry: ModuleContractRegistry | None = None


def _registry_instance() -> ModuleContractRegistry:
    """Lazily load and cache the module-contract registry."""
    global _registry
    if _registry is None:
        _registry = ModuleContractRegistry().load()
    return _registry


def humanize_actor(module_name: str) -> str:
    """Humanize a contract ``module_name`` into a sentence actor.

    "Document Center" -> "The document center". Falls back to a neutral actor
    for blank names so a malformed contract can never emit a broken sentence.
    """
    name = (module_name or "").strip()
    if not name:
        return "Semptify"
    return f"The {name.lower()}"


def render_narration(actor: str, event: NarratorEvent) -> str:
    """Assemble one narration line: '{Actor} {verb} {object} {context_clause}.'"""
    parts = f"{actor} {event.verb} {event.object} {event.context_clause}".split()
    sentence = " ".join(parts)
    if not sentence:
        return ""
    if sentence[-1] not in ".!?":
        sentence += "."
    return sentence[0].upper() + sentence[1:]


def resolve_narration(module_package: str | None, slot: Any) -> str | None:
    """Resolve a contract narrator slot to a rendered sentence.

    ``module_package`` is the contract registry key (e.g.
    ``app.modules.document_center``); ``slot`` is the index into its
    ``narrative_events`` list. Returns ``None`` when the contract or slot is
    missing so callers can fall back cleanly — narration is best-effort and
    must never raise across the WebSocket boundary.
    """
    if not module_package or slot is None:
        return None
    try:
        index = int(slot)
    except (TypeError, ValueError):
        return None
    try:
        contract = _registry_instance().get(str(module_package))
    except Exception as exc:  # registry load failure must never break the push
        logger.warning("narrator: contract registry load failed: %s", exc)
        return None
    if contract is None:
        return None
    if index < 0 or index >= len(contract.narrative_events):
        return None
    return render_narration(humanize_actor(contract.module_name), contract.narrative_events[index])


async def publish_narrated(
    event_type: Any,
    *,
    module_package: str,
    slot: int,
    data: dict[str, Any] | None = None,
    user_id: str | None = None,
    source: str = "system",
) -> None:
    """Publish a real backend event that carries a contract narration slot.

    ``slot`` is the index into the module's ``module_contract.json``
    ``narrative_events`` — the ws boundary renders only declared slots, so a
    narrated line always traces to a step the module declared and actually
    ran. The lazy ``event_bus`` import avoids an import cycle.
    """
    from app.core.event_bus import event_bus

    payload = dict(data or {})
    payload[NARRATOR_DATA_KEY] = {"module": module_package, "slot": slot}
    await event_bus.publish(event_type, payload, source=source, user_id=user_id)


__all__ = [
    "NARRATOR_DATA_KEY",
    "humanize_actor",
    "render_narration",
    "resolve_narration",
    "publish_narrated",
]
