"""Tests for the contract-driven Real-Time Narrator (ADR-0008 §2.3, Part 2)."""

from __future__ import annotations

import pytest

from app.core.module_contract import NarratorEvent
from app.core.narrator import (
    humanize_actor,
    render_narration,
    resolve_narration,
)


def test_render_narration_assembles_sentence():
    event = NarratorEvent(
        verb="is checking",
        object="the uploaded document",
        context_clause="because the tenant opened it in the Document Center viewer",
    )
    assert (
        render_narration("The document center", event)
        == "The document center is checking the uploaded document because the tenant opened it in the Document Center viewer."
    )


def test_render_narration_capitalizes_and_terminates():
    event = NarratorEvent(verb="found", object="extracted fields", context_clause="after OCR ran")
    sentence = render_narration("the timeline builder", event)
    assert sentence == "The timeline builder found extracted fields after OCR ran."
    assert sentence.endswith(".")


def test_humanize_actor():
    assert humanize_actor("Document Center") == "The document center"
    assert humanize_actor("  ") == "Semptify"
    assert humanize_actor("") == "Semptify"


def test_resolve_narration_real_contract():
    # document_center ships a real module_contract.json with narrative_events.
    line = resolve_narration("app.modules.document_center", 0)
    assert line is not None
    assert "is checking" in line
    assert line.endswith(".")


def test_resolve_narration_missing_slot_returns_none():
    assert resolve_narration("app.modules.document_center", 999) is None
    assert resolve_narration("app.modules.document_center", -1) is None


def test_resolve_narration_unknown_module_returns_none():
    assert resolve_narration("app.modules.does_not_exist", 0) is None
    assert resolve_narration(None, 0) is None
    assert resolve_narration("app.modules.document_center", "not-an-int") is None


@pytest.mark.asyncio
async def test_push_to_websockets_injects_contract_narration():
    """Contract-driven narration is injected at the ws boundary, not on the event."""
    from app.core.event_bus import Event, EventType, event_bus

    class _WS:
        def __init__(self):
            self.sent = []

        async def send_text(self, message):
            self.sent.append(message)

    ws = _WS()
    event_bus.register_websocket(ws, user_id="u1")
    try:
        event = Event(
            type=EventType.OCR_FAILED,
            data={"narrator": {"module": "app.modules.document_center", "slot": 0}},
            user_id="u1",
        )
        await event_bus._push_to_websockets(event, "u1")
    finally:
        event_bus.unregister_websocket(ws, user_id="u1")

    assert ws.sent, "expected a websocket payload"
    import json

    payload = json.loads(ws.sent[0])
    # Contract narration wins over the legacy NARRATION_MESSAGES fallback.
    assert "narration" in payload
    assert "is checking" in payload["narration"]
    assert payload["narration"].endswith(".")


@pytest.mark.asyncio
async def test_push_to_websockets_legacy_fallback_intact():
    """The four hardcoded upload messages still resolve via NARRATION_MESSAGES."""
    from app.core.event_bus import Event, EventType, event_bus

    class _WS:
        def __init__(self):
            self.sent = []

        async def send_text(self, message):
            self.sent.append(message)

    ws = _WS()
    event_bus.register_websocket(ws, user_id="u2")
    try:
        event = Event(type=EventType.DOCUMENT_UPLOAD_RECEIVED, data={}, user_id="u2")
        await event_bus._push_to_websockets(event, "u2")
    finally:
        event_bus.unregister_websocket(ws, user_id="u2")

    import json

    payload = json.loads(ws.sent[0])
    assert payload["narration"] == "Got your document — starting the scan now."
