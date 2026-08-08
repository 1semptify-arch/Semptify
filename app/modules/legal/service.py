"""
Legal Service
=============

File-based persistence for legal matters, court filings, discovery, and exhibits.
Storage layout (under DATA_DIR):
    matters/matter_<id>.json
    matters/matter_<id>/filings.json
    matters/matter_<id>/discovery.json
    matters/matter_<id>/exhibits.json

Each matter is a Pydantic model. All writes are atomic (write-then-replace).
"""

from __future__ import annotations

import json
import logging
import secrets
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from app.core.utc import utc_now

if TYPE_CHECKING:
    from datetime import date, datetime

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "legal_workspace"
MATTERS_DIR = DATA_DIR / "matters"
MATTERS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Pydantic Models
# =============================================================================


class Matter(BaseModel):
    matter_id: str
    title: str
    tenant_user_id: str | None = None
    tenant_name: str | None = None
    landlord_name: str | None = None
    address: str | None = None
    status: str = "open"  # open, closed, held
    notes: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    created_by: str | None = None


class CourtFiling(BaseModel):
    filing_id: str
    matter_id: str
    filing_type: str  # complaint, motion, answer, discovery, notice, brief
    court: str
    docket_number: str | None = None
    filing_date: date | None = None
    status: str = "draft"  # draft, filed, served, rejected
    notes: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class DiscoveryRecord(BaseModel):
    discovery_id: str
    matter_id: str
    discovery_type: str  # interrogatories, requests_for_production, requests_for_admission, depositions
    served_date: date | None = None
    due_date: date | None = None
    status: str = "pending"  # pending, served, responded, overdue
    responses: list[str] = []
    notes: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class Exhibit(BaseModel):
    exhibit_id: str
    matter_id: str
    exhibit_number: int
    description: str
    evidence_item_id: str | None = None
    vault_path: str | None = None
    introduced_on: date | None = None
    notes: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


# =============================================================================
# Helpers
# =============================================================================


def _matter_file(matter_id: str) -> Path:
    return MATTERS_DIR / f"matter_{matter_id}.json"


def _matter_dir(matter_id: str) -> Path:
    d = MATTERS_DIR / f"matter_{matter_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _filings_file(matter_id: str) -> Path:
    return _matter_dir(matter_id) / "filings.json"


def _discovery_file(matter_id: str) -> Path:
    return _matter_dir(matter_id) / "discovery.json"


def _exhibits_file(matter_id: str) -> Path:
    return _matter_dir(matter_id) / "exhibits.json"


def _gen_id(prefix: str = "") -> str:
    return f"{prefix}{secrets.token_hex(8)}"


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to read %s: %s", path, e)
        return default


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, default=str, indent=2), encoding="utf-8")


# =============================================================================
# Matter Operations
# =============================================================================


def create_matter(
    title: str,
    created_by: str | None = None,
    tenant_user_id: str | None = None,
    tenant_name: str | None = None,
    landlord_name: str | None = None,
    address: str | None = None,
    notes: str | None = None,
) -> Matter:
    matter = Matter(
        matter_id=_gen_id("m_"),
        title=title,
        created_by=created_by,
        tenant_user_id=tenant_user_id,
        tenant_name=tenant_name,
        landlord_name=landlord_name,
        address=address,
        notes=notes,
    )
    _write_json(_matter_file(matter.matter_id), matter.model_dump())
    return matter


def list_matters(created_by: str | None = None) -> list[Matter]:
    matters: list[Matter] = []
    for f in MATTERS_DIR.glob("matter_*.json"):
        try:
            m = Matter.model_validate_json(f.read_text(encoding="utf-8"))
            if created_by and m.created_by != created_by:
                continue
            matters.append(m)
        except Exception as e:
            logger.warning("Skipping invalid matter file %s: %s", f, e)
    matters.sort(key=lambda x: x.updated_at, reverse=True)
    return matters


def load_matter(matter_id: str) -> Matter:
    p = _matter_file(matter_id)
    if not p.exists():
        raise FileNotFoundError(f"Matter {matter_id} not found")
    return Matter.model_validate_json(p.read_text(encoding="utf-8"))


def update_matter(matter_id: str, **updates) -> Matter:
    m = load_matter(matter_id)
    data = m.model_dump()
    data.update(updates)
    data["updated_at"] = utc_now().isoformat()
    updated = Matter.model_validate(data)
    _write_json(_matter_file(matter_id), updated.model_dump())
    return updated


# =============================================================================
# Court Filings
# =============================================================================


def list_filings(matter_id: str) -> list[CourtFiling]:
    data = _read_json(_filings_file(matter_id), [])
    return [CourtFiling.model_validate(d) for d in data]


def add_filing(
    matter_id: str,
    filing_type: str,
    court: str,
    docket_number: str | None = None,
    filing_date: date | None = None,
    notes: str | None = None,
) -> CourtFiling:
    _ = load_matter(matter_id)  # ensure matter exists
    filing = CourtFiling(
        filing_id=_gen_id("f_"),
        matter_id=matter_id,
        filing_type=filing_type,
        court=court,
        docket_number=docket_number,
        filing_date=filing_date,
        notes=notes,
    )
    filings = [f.model_dump() for f in list_filings(matter_id)]
    filings.append(filing.model_dump())
    _write_json(_filings_file(matter_id), filings)
    return filing


def update_filing_status(matter_id: str, filing_id: str, status: str) -> CourtFiling:
    filings = list_filings(matter_id)
    for f in filings:
        if f.filing_id == filing_id:
            f.status = status
            break
    else:
        raise FileNotFoundError(f"Filing {filing_id} not found in matter {matter_id}")
    _write_json(_filings_file(matter_id), [f.model_dump() for f in filings])
    return next(f for f in filings if f.filing_id == filing_id)


# =============================================================================
# Discovery
# =============================================================================


def list_discovery(matter_id: str) -> list[DiscoveryRecord]:
    data = _read_json(_discovery_file(matter_id), [])
    return [DiscoveryRecord.model_validate(d) for d in data]


def add_discovery(
    matter_id: str,
    discovery_type: str,
    served_date: date | None = None,
    due_date: date | None = None,
    notes: str | None = None,
) -> DiscoveryRecord:
    _ = load_matter(matter_id)
    rec = DiscoveryRecord(
        discovery_id=_gen_id("d_"),
        matter_id=matter_id,
        discovery_type=discovery_type,
        served_date=served_date,
        due_date=due_date,
        notes=notes,
    )
    records = [r.model_dump() for r in list_discovery(matter_id)]
    records.append(rec.model_dump())
    _write_json(_discovery_file(matter_id), records)
    return rec


def update_discovery_status(
    matter_id: str,
    discovery_id: str,
    status: str,
    response_note: str | None = None,
) -> DiscoveryRecord:
    records = list_discovery(matter_id)
    for r in records:
        if r.discovery_id == discovery_id:
            r.status = status
            if response_note:
                r.responses = list(r.responses) + [response_note]
            break
    else:
        raise FileNotFoundError(f"Discovery {discovery_id} not found in matter {matter_id}")
    _write_json(_discovery_file(matter_id), [r.model_dump() for r in records])
    return next(r for r in records if r.discovery_id == discovery_id)


# =============================================================================
# Exhibits
# =============================================================================


def list_exhibits(matter_id: str) -> list[Exhibit]:
    data = _read_json(_exhibits_file(matter_id), [])
    return [Exhibit.model_validate(d) for d in data]


def add_exhibit(
    matter_id: str,
    description: str,
    evidence_item_id: str | None = None,
    vault_path: str | None = None,
    introduced_on: date | None = None,
    notes: str | None = None,
) -> Exhibit:
    _ = load_matter(matter_id)
    existing = list_exhibits(matter_id)
    next_num = max((e.exhibit_number for e in existing), default=0) + 1
    ex = Exhibit(
        exhibit_id=_gen_id("x_"),
        matter_id=matter_id,
        exhibit_number=next_num,
        description=description,
        evidence_item_id=evidence_item_id,
        vault_path=vault_path,
        introduced_on=introduced_on,
        notes=notes,
    )
    items = [e.model_dump() for e in existing]
    items.append(ex.model_dump())
    _write_json(_exhibits_file(matter_id), items)
    return ex


# =============================================================================
# Overlay Integration
# =============================================================================


def matter_overlay_payload(matter_id: str) -> dict:
    """Return a combined overlay payload for a matter (filings + discovery + exhibits)."""
    return {
        "matter_id": matter_id,
        "filings": [f.model_dump(mode="json") for f in list_filings(matter_id)],
        "discovery": [d.model_dump(mode="json") for d in list_discovery(matter_id)],
        "exhibits": [e.model_dump(mode="json") for e in list_exhibits(matter_id)],
        "generated_at": utc_now().isoformat(),
    }
