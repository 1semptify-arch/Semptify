"""Pattern record store — PATTERN_RECORD overlays in the tenant's cloud vault.

Pattern detection records persist as overlays anchored to
`document_id="patterns:{user_id}"` at VAULT_DERIVED_FILE (derived tenant data —
regenerated analysis artifacts still belong to the tenant, not the server).
Legacy `pattern_records` rows migrate on first read: non-destructive,
idempotent via `payload["legacy_id"]`, bounded at 25 rows/call.

The legacy PK is an autoincrement INTEGER used in `/record/{record_id}` URL
paths — payload["record_id"] preserves it (new records allocate max+1 per
user) so int-path callers keep working.

Persistence stays env-gated (ENABLE_PATTERN_PERSISTENCE=true) — all public
functions return empty/None when disabled, matching legacy semantics.

View contract: list/get return view objects carrying the ORM surface used by
the pattern_history router (id:int, user_id, analysis_type, patterns,
risk_score, risk_level, data_sources, algorithm_version, created_at,
reviewed, notes, pattern_count, pattern_types, to_dict()).
"""

import logging
from datetime import datetime, timedelta
from types import SimpleNamespace

from app.core.overlay_types import OverlayType
from app.core.utc import utc_now
from app.core.user_context import UserContext, build_context_for_user_id
from app.core.vault_paths import VAULT_DERIVED_FILE
from app.models.unified_overlay_models import CreateOverlayRequest
from app.services.storage import get_provider
from app.services.unified_overlay_manager import UnifiedOverlayManager, get_unified_overlay_manager

logger = logging.getLogger(__name__)

PATTERN_FIELDS = (
    "analysis_type",
    "patterns",
    "risk_score",
    "risk_level",
    "data_sources",
    "algorithm_version",
    "reviewed",
    "notes",
)


def is_pattern_persistence_enabled() -> bool:
    """Check if pattern persistence is enabled in environment."""
    import os

    return os.getenv("ENABLE_PATTERN_PERSISTENCE", "false").lower() == "true"


def _anchor(effective_id: str) -> str:
    return f"patterns:{effective_id}"


async def _get_manager(user: UserContext) -> UnifiedOverlayManager:
    """Manager keyed to the effective user so impersonation writes belong to the tenant."""
    storage = get_provider(user.provider.value, access_token=user.access_token)
    return await get_unified_overlay_manager(storage, user.get_effective_user_id())


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _to_iso(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class PatternRecordView(SimpleNamespace):
    """ORM-compatible surface: attributes + to_dict() + pattern properties."""

    @property
    def pattern_count(self) -> int:
        return len((self.patterns or {}).get("patterns", []))

    @property
    def pattern_types(self) -> list:
        patterns = (self.patterns or {}).get("patterns", [])
        return list({p.get("type") for p in patterns if p.get("type")})

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "analysis_type": self.analysis_type,
            "patterns": self.patterns,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "data_sources": self.data_sources,
            "algorithm_version": self.algorithm_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reviewed": self.reviewed,
            "notes": self.notes,
            "pattern_count": self.pattern_count,
            "pattern_types": self.pattern_types,
        }


def _view(overlay, effective_id: str) -> PatternRecordView:
    p = overlay.payload
    return PatternRecordView(
        id=p.get("record_id"),
        user_id=effective_id,
        analysis_type=p.get("analysis_type"),
        patterns=p.get("patterns") or {},
        risk_score=p.get("risk_score") or 0,
        risk_level=p.get("risk_level") or "unknown",
        data_sources=p.get("data_sources") or {},
        algorithm_version=p.get("algorithm_version") or "1.0",
        created_at=_parse_dt(p.get("created_at")) or overlay.created_at,
        reviewed=bool(p.get("reviewed")),
        notes=p.get("notes"),
        overlay_id=overlay.overlay_id,
    )


async def _list_overlays(user: UserContext) -> list:
    manager = await _get_manager(user)
    effective_id = user.get_effective_user_id()
    response = await manager.get_overlays(document_id=_anchor(effective_id), overlay_type=OverlayType.PATTERN_RECORD)
    if not response.success:
        logger.warning("Pattern overlay list failed for user %s: %s", user.user_id[:8], response.message)
        return []
    return [o for o in response.overlays if o.created_by == effective_id]


async def _resolve_overlay(user: UserContext, record_id):
    try:
        wanted = int(record_id)
    except (TypeError, ValueError):
        wanted = None
    for o in await _list_overlays(user):
        if o.overlay_id == record_id or (wanted is not None and o.payload.get("record_id") == wanted):
            return o
    return None


async def save_pattern_record(
    user: UserContext,
    analysis_type: str,
    pattern_data: dict,
    data_sources: dict | None = None,
    notes: str | None = None,
) -> PatternRecordView | None:
    """Persist a pattern detection record. Returns None when persistence is
    disabled or the write fails (callers treat persistence as optional)."""
    if not is_pattern_persistence_enabled():
        return None
    effective_id = user.get_effective_user_id()
    manager = await _get_manager(user)

    existing = await _list_overlays(user)
    int_ids = [o.payload.get("record_id") for o in existing if isinstance(o.payload.get("record_id"), int)]
    next_id = (max(int_ids) + 1) if int_ids else 1

    payload = {
        "record_id": next_id,
        "analysis_type": analysis_type,
        "patterns": pattern_data or {},
        "risk_score": (pattern_data or {}).get("summary", {}).get("risk_score", 0),
        "risk_level": (pattern_data or {}).get("summary", {}).get("risk_level", "unknown"),
        "data_sources": data_sources or {},
        "algorithm_version": "1.0",
        "created_at": utc_now().isoformat(),
        "reviewed": False,
        "notes": notes,
    }
    response = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.PATTERN_RECORD,
            document_id=_anchor(effective_id),
            vault_path=VAULT_DERIVED_FILE,
            payload=payload,
            metadata={"analysis_type": analysis_type, "scope": "patterns"},
        )
    )
    if not response.success or not response.overlay_id:
        logger.error("Failed to save pattern record for user %s: %s", user.user_id[:8], response.message)
        return None
    overlay = await manager.get_overlay(response.overlay_id)
    return _view(overlay, effective_id) if overlay else None


async def get_pattern_history(user: UserContext, limit: int = 50) -> list[PatternRecordView]:
    """Newest-first history for the user (legacy rows migrate first)."""
    if not is_pattern_persistence_enabled():
        return []
    await migrate_legacy_records(user)
    overlays = await _list_overlays(user)
    overlays.sort(key=lambda o: o.payload.get("created_at") or "", reverse=True)
    effective_id = user.get_effective_user_id()
    return [_view(o, effective_id) for o in overlays[:limit]]


async def get_pattern_record(user: UserContext, record_id) -> PatternRecordView | None:
    if not is_pattern_persistence_enabled():
        return None
    await migrate_legacy_records(user)
    overlay = await _resolve_overlay(user, record_id)
    if not overlay:
        return None
    return _view(overlay, user.get_effective_user_id())


async def mark_pattern_reviewed(user: UserContext, record_id, notes: str | None = None) -> PatternRecordView | None:
    if not is_pattern_persistence_enabled():
        return None
    overlay = await _resolve_overlay(user, record_id)
    if not overlay:
        return None
    overlay.payload["reviewed"] = True
    if notes:
        overlay.payload["notes"] = notes
    manager = await _get_manager(user)
    await manager.update_overlay(overlay.overlay_id, payload=overlay.payload)
    return _view(overlay, user.get_effective_user_id())


async def get_pattern_trends(user: UserContext, days: int = 30) -> dict:
    """Daily average risk scores + pattern-type frequency over the window."""
    if not is_pattern_persistence_enabled():
        return {}
    records = await get_pattern_history(user, limit=500)
    cutoff = utc_now() - timedelta(days=days)
    window = [r for r in records if r.created_at and r.created_at >= cutoff]

    daily: dict[str, list[int]] = {}
    type_counts: dict[str, int] = {}
    for r in window:
        day = r.created_at.date().isoformat()
        daily.setdefault(day, []).append(r.risk_score or 0)
        for p in (r.patterns or {}).get("patterns", []):
            ptype = p.get("type", "unknown")
            type_counts[ptype] = type_counts.get(ptype, 0) + 1

    return {
        "period_days": days,
        "daily_averages": [
            {"date": day, "avg_risk": sum(scores) / len(scores), "count": len(scores)}
            for day, scores in sorted(daily.items())
        ],
        "pattern_type_frequency": type_counts,
        "total_analyses": len(window),
    }


async def get_pattern_stats(user: UserContext) -> dict:
    """Aggregate stats for the /stats endpoint (totals, risk distribution, recent)."""
    records = await get_pattern_history(user, limit=500)
    if not records:
        return {
            "total_analyses": 0,
            "average_risk_score": 0,
            "most_common_risk_level": "none",
            "pattern_types": [],
            "recent_analyses": [],
        }
    risk_counts: dict[str, int] = {}
    for r in records:
        risk_counts[r.risk_level] = risk_counts.get(r.risk_level, 0) + 1
    all_types: list[str] = []
    for r in records:
        all_types.extend(r.pattern_types)
    return {
        "total_analyses": len(records),
        "average_risk_score": round(sum(r.risk_score or 0 for r in records) / len(records), 2),
        "most_common_risk_level": max(risk_counts.items(), key=lambda x: x[1])[0],
        "risk_level_distribution": risk_counts,
        "pattern_types": sorted(set(all_types)),
        "recent_analyses": [r.to_dict() for r in records[:5]],
    }


async def get_pattern_history_for_user_id(user_id: str, limit: int = 50) -> list[PatternRecordView]:
    user = await build_context_for_user_id(user_id)
    return await get_pattern_history(user, limit)


async def migrate_legacy_records(user: UserContext, limit: int = 25) -> int:
    """Bounded import of legacy `pattern_records` rows. Non-destructive,
    idempotent via payload["legacy_id"]; preserves the integer PK in
    payload["record_id"] so /record/{id} URLs keep resolving."""
    try:
        from sqlalchemy import select

        from app.core.database import get_db_session
        from app.models.pattern_record import PatternRecord
    except Exception:
        return 0

    effective_id = user.get_effective_user_id()
    imported = 0
    try:
        overlays = await _list_overlays(user)
        migrated_ids = {o.payload.get("legacy_id") for o in overlays if o.payload.get("legacy_id") is not None}
        manager = await _get_manager(user)

        async with get_db_session() as db:
            result = await db.execute(
                select(PatternRecord).where(PatternRecord.user_id == user.user_id).order_by(PatternRecord.id).limit(limit)
            )
            for row in result.scalars().all():
                if imported >= limit or row.id in migrated_ids:
                    continue
                await manager.create_overlay(
                    CreateOverlayRequest(
                        overlay_type=OverlayType.PATTERN_RECORD,
                        document_id=_anchor(effective_id),
                        vault_path=VAULT_DERIVED_FILE,
                        payload={
                            "record_id": row.id,
                            "analysis_type": row.analysis_type,
                            "patterns": row.patterns or {},
                            "risk_score": row.risk_score,
                            "risk_level": row.risk_level,
                            "data_sources": row.data_sources or {},
                            "algorithm_version": row.algorithm_version,
                            "created_at": row.created_at.isoformat() if row.created_at else None,
                            "reviewed": bool(row.reviewed),
                            "notes": row.notes,
                            "legacy_id": row.id,
                            "migrated_from": "pattern_records",
                        },
                        metadata={"analysis_type": row.analysis_type, "scope": "patterns"},
                    )
                )
                migrated_ids.add(row.id)
                imported += 1
    except Exception:
        logger.exception("Legacy pattern-record migration failed for user %s", user.user_id[:8])
        return imported

    return imported
