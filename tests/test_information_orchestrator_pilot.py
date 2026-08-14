"""End-to-end pilot test for ADR-0008 Information Orchestrator.

Tests the pilot across the two declared surfaces:
- Eviction Timeline (todo-073)
- Vault upload flow (todo-074)

Verifies:
  * Object + Page Envelope resolution
  * Layer 1 curated content store + Layer 2 metadata-match retrieval
  * Live Event-Driven Narration over WebSocket events
  * Familiarity Tapering
  * Momentum / Emotional Checkpoints
  * Experience Token read/write (no server-side persistence of user state)

This test does NOT expand beyond the two pilot surfaces.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.core.context_envelope import (
    EncounterContext,
    ObjectEnvelope,
    ObjectType,
    Pillar,
    Provenance,
    TemporalValidity,
    Who,
    resolve_envelope,
)
from app.core.event_bus import (
    EventBus,
    EventType,
    NARRATION_MESSAGES,
    publish_event,
)
from app.core.experience_token import (
    ExperienceToken,
    load_experience_token,
    record_exposure,
)
from app.core.page_envelope import PageEnvelope
from app.modules.context_engine.explanation_entries import (
    ContextExplanationEntry,
    create_explanation_entry,
    get_explanation_entries,
)
from app.modules.context_engine.retrieval import (
    LAYER2_CONFIDENCE_THRESHOLD,
    RetrievalResult,
    retrieve_explanations,
    select_tapered_variant,
)
from app.modules.eviction_timeline.envelopes import (
    EVICTION_TIMELINE_PAGE,
    get_eviction_timeline_page,
)
from app.modules.vault.envelopes import (
    VAULT_UPLOAD_PAGE,
    get_vault_upload_page,
    vault_document_to_object_envelope,
)
from app.services.emotion_engine import get_momentum_checkpoint
from app.services.vault_upload_service import VaultDocument


# =============================================================================
# 1. Object + Page Envelope resolution
# =============================================================================


@pytest.mark.anyio
async def test_eviction_timeline_page_envelope_resolves():
    page = await get_eviction_timeline_page(EncounterContext())
    assert isinstance(page, PageEnvelope)
    assert page.page_subject == "Eviction Timeline"
    assert len(page.page_actions) == 6
    for action in page.page_actions:
        assert action.journey_stage is not None


@pytest.mark.anyio
async def test_vault_upload_page_envelope_resolves():
    page = await get_vault_upload_page(EncounterContext())
    assert isinstance(page, PageEnvelope)
    assert page.page_subject == "Document Vault"
    assert len(page.page_actions) == 4
    for action in page.page_actions:
        assert action.journey_stage is not None


@pytest.mark.anyio
async def test_vault_document_has_object_envelope():
    doc = VaultDocument(
        vault_id="doc_abc",
        user_id="GUtest1234",
        filename="notice.pdf",
        safe_filename="doc_abc_notice.pdf",
        sha256_hash="abc",
        file_size=100,
        mime_type="application/pdf",
        document_type="eviction_notice",
        description=None,
        tags=[],
        storage_path="vault/notice.pdf",
        storage_provider="local",
        source_module="vault_router",
    )
    envelope = vault_document_to_object_envelope(doc)
    assert isinstance(envelope, ObjectEnvelope)
    assert envelope.object_id == "doc_abc"
    assert "eviction_notice" in envelope.subject_tags
    assert envelope.pillar == Pillar.RECORD


# =============================================================================
# 2. Layer 1 content store + Layer 2 metadata-match retrieval
# =============================================================================


@pytest.mark.anyio
async def test_layer_1_entry_creation_and_read():
    entry = await create_explanation_entry(
        subject="eviction",
        jurisdiction="MN",
        upl_risk_tier="LOW",
        pillar="KNOW",
        review_status="VETTED",
        variant_trust="Why this matters.",
        variant_mechanics="What actually happens.",
        variant_reinforcement="Short reminder.",
        variant_minimal="Logged.",
    )
    assert isinstance(entry, ContextExplanationEntry)
    assert entry.entry_id.startswith("exp_")

    entries = await get_explanation_entries(subject="eviction", jurisdiction="MN")
    assert any(e.entry_id == entry.entry_id for e in entries)


@pytest.mark.anyio
async def test_layer_2_retrieval_matches_object_envelope():
    entry = await create_explanation_entry(
        subject="eviction",
        jurisdiction="MN",
        upl_risk_tier="LOW",
        pillar="KNOW",
        review_status="VETTED",
        variant_trust="Why this matters.",
        variant_mechanics="What actually happens.",
        variant_reinforcement="Short reminder.",
        variant_minimal="Logged.",
    )

    obj = ObjectEnvelope(
        object_id="notice_date",
        object_type=ObjectType.FIELD,
        pillar=Pillar.KNOW,
        who=Who.TENANT,
        why="Tracks the date on an eviction notice.",
        provenance=Provenance.OCR_EXTRACTED,
        temporal_validity=TemporalValidity.TIME_BOUND,
        subject_tags=["eviction"],
    )

    results = await retrieve_explanations(obj, jurisdiction="MN")
    assert len(results) >= 1
    assert all(r.score >= LAYER2_CONFIDENCE_THRESHOLD for r in results)
    assert any(r.entry_id == entry.entry_id for r in results)


# =============================================================================
# 3. Familiarity Tapering
# =============================================================================


def test_familiarity_tapering_maps_exposure_to_variants():
    result = RetrievalResult(
        entry_id="exp_123",
        subject="eviction",
        jurisdiction="MN",
        upl_risk_tier="LOW",
        pillar="KNOW",
        review_status="VETTED",
        score=1.0,
        variant_trust="trust",
        variant_mechanics="mechanics",
        variant_reinforcement="reinforcement",
        variant_minimal="minimal",
    )
    assert select_tapered_variant(result, 1) == "mechanics"
    assert select_tapered_variant(result, 2) == "trust"
    assert select_tapered_variant(result, 3) == "reinforcement"
    assert select_tapered_variant(result, 4) == "minimal"
    assert select_tapered_variant(result, 10) == "minimal"


@pytest.mark.anyio
async def test_experience_token_records_exposure():
    token = ExperienceToken()
    count, updated = record_exposure(token, "field")
    assert count == 1
    assert updated.exposure_tallies["field"] == 1
    # Original token is not mutated.
    assert "field" not in token.exposure_tallies


# =============================================================================
# 4. Momentum / Emotional Checkpoints
# =============================================================================


def test_momentum_checkpoint_warm_and_scales_by_intensity():
    # Intensity 0 suppresses.
    assert get_momentum_checkpoint("phase_complete", "notice", "answer", 0) is None
    # Intensity 2 returns the standard message.
    msg = get_momentum_checkpoint("phase_complete", "notice", "answer", 2)
    assert msg is not None
    assert "notice" in msg.lower()
    # Should never contain urgency/fear framing.
    assert "urgent" not in msg.lower()
    assert "fear" not in msg.lower()


# =============================================================================
# 5. Live Event-Driven Narration
# =============================================================================


@pytest.mark.anyio
async def test_narration_events_carry_narration_in_websocket_payload():
    bus = EventBus()
    ws = AsyncMock()
    bus.register_websocket(ws, user_id="GUtest1234")

    await publish_event(
        EventType.DOCUMENT_UPLOAD_RECEIVED,
        {"vault_id": "doc_123", "filename": "notice.pdf"},
        source="vault",
        user_id="GUtest1234",
    )

    assert ws.send_text.call_count == 1
    payload = json.loads(ws.send_text.call_args.args[0])
    assert payload["narration"] == NARRATION_MESSAGES[EventType.DOCUMENT_UPLOAD_RECEIVED]


@pytest.mark.anyio
async def test_non_narration_events_do_not_carry_narration():
    bus = EventBus()
    ws = AsyncMock()
    bus.register_websocket(ws, user_id="GUtest1234")

    await publish_event(
        EventType.TIMELINE_UPDATED,
        {"events_count": 3},
        source="timeline",
        user_id="GUtest1234",
    )

    payload = json.loads(ws.send_text.call_args.args[0])
    assert "narration" not in payload


# =============================================================================
# 6. Experience Token is not persisted server-side keyed to a user
# =============================================================================


@pytest.mark.anyio
async def test_experience_token_falls_back_to_session_default_without_storage():
    """ADR-0008 §3 hard constraint: no server-side table keyed to tenant/user.

    When the tenant has no connected cloud storage (or no valid OAuth), the
    Experience Token must return a fresh default. It must never be read from a
    server-side table keyed to the user.
    """
    token = await load_experience_token("GUtest1234")
    assert isinstance(token, ExperienceToken)
    assert token.intensity_level == 2  # default Standard


def test_experience_token_record_exposure_is_pure_and_stateless():
    """record_exposure must not mutate the input token or touch any storage."""
    original = ExperienceToken()
    count, updated = record_exposure(original, "field")
    assert count == 1
    assert updated is not original
    assert updated.exposure_tallies == {"field": 1}
    assert original.exposure_tallies == {}
