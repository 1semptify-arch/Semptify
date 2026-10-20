"""Settlement Awareness — gate, surface, and recheck tests.

Proves the Part 3B contract is mechanical, not advisory:

- intake can never skip the queue (always lands Unresolved)
- resolve refuses on each individual gate field
- news authorities cannot resolve without a primary source
- the consumer surface returns only records passing every gate
- staleness (>90 days unverified) auto-hides a previously-good record
- a failed recheck auto-hides without deleting anything

Run locally: python -m pytest app/modules/settlement_awareness/tests -v
"""

from datetime import timedelta

import pytest

from app.core.utc import utc_now
from app.modules.settlement_awareness import service
from app.modules.settlement_awareness.models import SettlementOrCaseRecord
from app.core.database import get_db_session


async def _intake(**overrides):
    """Create a raw Unresolved record and return its record_id."""
    kwargs = {
        "title": "Doe v. Big Apartments LLC — deposit withholding settlement",
        "subject": "deposit",
        "source_url": "https://example.mncourts.gov/opinion/12345",
        "citation": "Minn. Stat. § 504B.178",
        "source_authority": "mn_courts",
    }
    kwargs.update(overrides)
    async with get_db_session() as db:
        record = await service.create_record(db, **kwargs)
        return record.record_id


@pytest.mark.anyio
async def test_intake_lands_unresolved():
    rid = await _intake()
    async with get_db_session() as db:
        rec = (await db.get(SettlementOrCaseRecord,
                            (await _pk(db, rid))))
        assert rec.resolution_status == "Unresolved"
        assert rec.is_verified is False
        assert rec.fabrication_check is False


async def _pk(db, record_id):
    from sqlalchemy import select
    return (await db.execute(
        select(SettlementOrCaseRecord.id)
        .where(SettlementOrCaseRecord.record_id == record_id)
    )).scalar_one()


@pytest.mark.anyio
async def test_intake_rejects_bad_subject_and_empty_source():
    with pytest.raises(service.GateError):
        await _intake(subject="not_a_taxonomy_subject")
    with pytest.raises(service.GateError):
        await _intake(source_url="   ")
    with pytest.raises(service.GateError):
        await _intake(record_kind="prediction")


@pytest.mark.anyio
async def test_resolve_refuses_without_fabrication_check():
    rid = await _intake()
    async with get_db_session() as db:
        with pytest.raises(service.GateError):
            await service.resolve_record(db, rid, attested_by="brad",
                                         fabrication_check=False)


@pytest.mark.anyio
async def test_resolve_refuses_without_attestor():
    rid = await _intake()
    async with get_db_session() as db:
        with pytest.raises(service.GateError):
            await service.resolve_record(db, rid, attested_by="",
                                         fabrication_check=True)


@pytest.mark.anyio
async def test_news_source_cannot_resolve_without_primary():
    rid = await _intake(source_authority="news_star_tribune")
    async with get_db_session() as db:
        with pytest.raises(service.GateError):
            await service.resolve_record(db, rid, attested_by="brad",
                                         fabrication_check=True)


@pytest.mark.anyio
async def test_resolve_success_then_surface():
    rid = await _intake()
    async with get_db_session() as db:
        await service.resolve_record(db, rid, attested_by="brad",
                                     fabrication_check=True)
    async with get_db_session() as db:
        out = await service.related(db, subject="deposit")
        assert len(out) == 1
        assert out[0]["record_id"] == rid
        assert "disclaimer" in out[0]


@pytest.mark.anyio
async def test_citation_match_is_normalised():
    rid = await _intake(citation="Minn. Stat. § 504B.178")
    async with get_db_session() as db:
        await service.resolve_record(db, rid, attested_by="brad",
                                     fabrication_check=True)
    async with get_db_session() as db:
        out = await service.related(db, citation="504b178")
        assert len(out) == 1


@pytest.mark.anyio
async def test_unresolved_never_surfaces():
    await _intake()
    async with get_db_session() as db:
        out = await service.related(db, subject="deposit")
        assert out == []


@pytest.mark.anyio
async def test_stale_record_auto_hides():
    rid = await _intake()
    async with get_db_session() as db:
        await service.resolve_record(db, rid, attested_by="brad",
                                     fabrication_check=True)
        # Age the verification past the 90-day threshold
        rec = await db.get(SettlementOrCaseRecord, await _pk(db, rid))
        rec.last_verified_date = (
            utc_now() - timedelta(days=120)).strftime("%Y-%m-%d")
    async with get_db_session() as db:
        assert await service.related(db, subject="deposit") == []
        assert await service.get_surfaceable(db, rid) is None


@pytest.mark.anyio
async def test_failed_recheck_auto_hides():
    rid = await _intake()
    async with get_db_session() as db:
        await service.resolve_record(db, rid, attested_by="brad",
                                     fabrication_check=True)
    async with get_db_session() as db:
        await service.record_recheck(db, rid, source_still_live=False,
                                     verified_by="brad")
    async with get_db_session() as db:
        assert await service.related(db, subject="deposit") == []
        # And it lands on the recheck worklist
        due = await service.due_for_recheck(db)
        assert any(d["record_id"] == rid for d in due)


@pytest.mark.anyio
async def test_successful_recheck_keeps_surface_and_reschedules():
    rid = await _intake()
    async with get_db_session() as db:
        await service.resolve_record(db, rid, attested_by="brad",
                                     fabrication_check=True)
        rec = await db.get(SettlementOrCaseRecord, await _pk(db, rid))
        rec.next_recheck_date = "2000-01-01"  # force due
    async with get_db_session() as db:
        due = await service.due_for_recheck(db)
        assert any(d["record_id"] == rid for d in due)
        await service.record_recheck(db, rid, source_still_live=True,
                                     verified_by="brad")
    async with get_db_session() as db:
        out = await service.related(db, subject="deposit")
        assert len(out) == 1


@pytest.mark.anyio
async def test_public_dict_never_leaks_intake_fields():
    rid = await _intake()
    async with get_db_session() as db:
        await service.resolve_record(db, rid, attested_by="brad",
                                     fabrication_check=True)
    async with get_db_session() as db:
        out = await service.get_surfaceable(db, rid)
        for field in ("ai_generated", "fabrication_check",
                      "resolution_status", "resolution_method",
                      "next_recheck_date"):
            assert field not in out
