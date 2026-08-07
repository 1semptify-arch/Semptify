"""
Pattern Record Model - Optional persistence for housing accountability patterns

This model allows storing pattern detection results for historical tracking
and trend analysis. Patterns are stored as structured JSON with metadata.

Usage is optional - patterns can be generated on-demand without persistence.
Enable pattern persistence by setting ENABLE_PATTERN_PERSISTENCE=true in .env
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.utc import utc_now

logger = logging.getLogger(__name__)


class PatternRecord(Base):
    """Historical record of detected housing accountability patterns."""

    __tablename__ = "pattern_records"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # User and context
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "comprehensive", "fee_focus", etc.

    # Pattern data (structured JSON)
    patterns: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)  # "low", "medium", "high", "critical"

    # Source data references (for audit trail)
    data_sources: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=True)  # Which documents/events contributed
    algorithm_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)  # Human reviewed?
    notes: Mapped[str] = mapped_column(Text, nullable=True)  # Analyst notes

    def __repr__(self):
        return f"<PatternRecord user={self.user_id[:8]}*** risk={self.risk_level} score={self.risk_score}>"

    @property
    def pattern_count(self) -> int:
        """Get total number of patterns in this record."""
        return len(self.patterns.get("patterns", []))

    @property
    def pattern_types(self) -> list:
        """Get unique pattern types detected."""
        patterns = self.patterns.get("patterns", [])
        return list(set(p.get("type") for p in patterns if p.get("type")))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
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


# Pattern persistence configuration
def is_pattern_persistence_enabled() -> bool:
    """Check if pattern persistence is enabled in environment."""
    import os
    return os.getenv("ENABLE_PATTERN_PERSISTENCE", "false").lower() == "true"


def save_pattern_record(
    db_session,
    user_id: str,
    analysis_type: str,
    pattern_data: dict[str, Any],
    data_sources: dict[str, Any] | None = None,
    notes: str | None = None
) -> PatternRecord | None:
    """
    Save a pattern record to database if persistence is enabled.
    
    Returns:
        PatternRecord if saved, None if persistence disabled
    """
    if not is_pattern_persistence_enabled():
        return None

    try:
        record = PatternRecord(
            user_id=user_id,
            analysis_type=analysis_type,
            patterns=pattern_data,
            risk_score=pattern_data.get("summary", {}).get("risk_score", 0),
            risk_level=pattern_data.get("summary", {}).get("risk_level", "unknown"),
            data_sources=data_sources or {},
            algorithm_version="1.0",
            created_at=utc_now(),
            notes=notes
        )

        db_session.add(record)
        db_session.commit()
        return record

    except Exception as e:
        db_session.rollback()
        raise e


def get_pattern_history(
    db_session,
    user_id: str,
    limit: int = 50
) -> list[PatternRecord]:
    """
    Get pattern history for a user if persistence is enabled.
    
    Returns:
        List of PatternRecord sorted by created_at desc, empty list if disabled
    """
    if not is_pattern_persistence_enabled():
        return []

    try:
        from sqlalchemy import desc, select

        result = db_session.execute(
            select(PatternRecord)
            .where(PatternRecord.user_id == user_id)
            .order_by(desc(PatternRecord.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    except Exception:
        return []


def get_pattern_trends(
    db_session,
    user_id: str,
    days: int = 30
) -> dict[str, Any]:
    """
    Analyze pattern trends over time if persistence is enabled.
    
    Returns:
        Dictionary with trend analysis or empty dict if disabled
    """
    if not is_pattern_persistence_enabled():
        return {}

    try:
        from datetime import timedelta

        from sqlalchemy import and_, func, select

        cutoff_date = utc_now() - timedelta(days=days)

        # Get average risk score over time
        result = db_session.execute(
            select(
                func.date(PatternRecord.created_at).label('date'),
                func.avg(PatternRecord.risk_score).label('avg_risk'),
                func.count(PatternRecord.id).label('count')
            )
            .where(and_(
                PatternRecord.user_id == user_id,
                PatternRecord.created_at >= cutoff_date
            ))
            .group_by(func.date(PatternRecord.created_at))
            .order_by(func.date(PatternRecord.created_at))
        )

        daily_data = []
        for row in result:
            daily_data.append({
                "date": row.date.isoformat(),
                "avg_risk": float(row.avg_risk) if row.avg_risk else 0,
                "count": row.count
            })

        # Get most common pattern types
        patterns_result = db_session.execute(
            select(PatternRecord.patterns)
            .where(and_(
                PatternRecord.user_id == user_id,
                PatternRecord.created_at >= cutoff_date
            ))
        )

        type_counts = {}
        for row in patterns_result:
            patterns = row.patterns or {}
            for pattern in patterns.get("patterns", []):
                ptype = pattern.get("type", "unknown")
                type_counts[ptype] = type_counts.get(ptype, 0) + 1

        return {
            "period_days": days,
            "daily_averages": daily_data,
            "pattern_type_frequency": type_counts,
            "total_analyses": len(daily_data)
        }

    except Exception:
        return {}
