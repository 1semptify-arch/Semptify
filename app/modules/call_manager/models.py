"""Call Manager model — per-call outreach log.

Stores what ACT! would call an activity record: who was called, which script
ran, the tapped outcome, key facts captured during the call (names, dates,
figures — the things the tenant is worst positioned to type), and the
follow-up commitment. Calendar/journal/timeline writes happen in the router
at save time so a completed call lands everywhere at once.
"""

from datetime import datetime

from sqlalchemy import (
    Integer,
    String,
    DateTime,
    Text,
)
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.utc import utc_now


class CallLog(Base):
    """One logged call (or call attempt) in the tenant's outreach history."""

    __tablename__ = "call_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # Snapshot of who was called — survives even if the contact overlay changes.
    contact_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_role: Mapped[str | None] = mapped_column(String(40), nullable=True)

    script_key: Mapped[str | None] = mapped_column(String(60), nullable=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=False, default="outbound")
    # no_answer | voicemail | spoke | callback_scheduled | accepted | declined | info_only | refused
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Tap-captured facts: [{"label": "Spoke with", "value": "Patty"}, ...]
    key_facts: Mapped[list | None] = mapped_column(JSON, nullable=True)

    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    follow_up_note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
