"""
Timeline chronology mechanics service.

Function Group: timeline_chronology
Purpose: Build a deterministic, ordered chronology payload for timeline presentation.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.module_contracts import FunctionGroupContract, register_function_group
from app.models.models import Document, DocumentPipelineIndex

TIMELINE_FUNCTION_GROUP = "timeline_chronology"

register_function_group(
    FunctionGroupContract(
        module="timeline",
        group_name=TIMELINE_FUNCTION_GROUP,
        title="Timeline Chronology Builder",
        description="Build deterministic timeline chronology from cloud events and indexed document metadata.",
        inputs=(
            "events",
            "db_session",
        ),
        outputs=(
            "chronology_items",
        ),
        dependencies=(
            "Semptify5.0/Vault/timeline/events.json",
            "documents",
            "document_pipeline_index",
        ),
        deterministic=True,
    )
)


def _parse_any_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value).strip()
        if not raw:
            return None
        dt = None
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            pass
        if dt is None:
            for fmt in (
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%m-%d-%Y",
                "%B %d, %Y",
                "%d %B %Y",
            ):
                try:
                    dt = datetime.strptime(raw, fmt)
                    break
                except ValueError:
                    continue
        if dt is None:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _display_datetime(value: Any) -> str:
    dt = _parse_any_datetime(value)
    if not dt:
        return "Unknown"
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


async def build_timeline_chronology(
    events: list[dict[str, Any]],
    db: AsyncSession,
) -> list[dict[str, Any]]:
    """
    Build ordered timeline chronology from extracted cloud events plus DB doc metadata.

    Ordering priority:
    1) Event occurrence time (`date`)
    2) Semptify ingestion time (`uploaded_at` or `extracted_at`)
    """
    chronology_items: list[dict[str, Any]] = []
    doc_metadata: dict[str, dict[str, str | None]] = {}

    source_doc_ids = {
        str(event.get("source_document_id", "")).strip()
        for event in events
        if isinstance(event, dict) and event.get("source_document_id")
    }

    if source_doc_ids:
        docs = (
            await db.execute(
                select(Document.id, Document.uploaded_at, Document.original_filename).where(
                    Document.id.in_(source_doc_ids)
                )
            )
        ).all()
        for doc_id, uploaded_at, original_filename in docs:
            doc_metadata[str(doc_id)] = {
                "uploaded_at": uploaded_at.isoformat() if uploaded_at else None,
                "original_filename": original_filename,
                "document_created_at": None,
            }

        index_rows = (
            await db.execute(
                select(DocumentPipelineIndex.doc_id, DocumentPipelineIndex.payload_json).where(
                    DocumentPipelineIndex.doc_id.in_(source_doc_ids)
                )
            )
        ).all()
        for doc_id, payload_json in index_rows:
            if not payload_json:
                continue
            try:
                payload = json.loads(payload_json)
            except (TypeError, ValueError):
                continue
            created_guess = payload.get("document_date") or payload.get("created_at")
            key = str(doc_id)
            if key not in doc_metadata:
                doc_metadata[key] = {
                    "uploaded_at": None,
                    "original_filename": None,
                    "document_created_at": None,
                }
            if created_guess:
                doc_metadata[key]["document_created_at"] = str(created_guess)

    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        source_document_id = str(event.get("source_document_id", "")).strip() or None
        linked_doc = doc_metadata.get(source_document_id or "", {})

        event_at_raw = event.get("date")
        document_created_at_raw = linked_doc.get("document_created_at")
        ingested_at_raw = linked_doc.get("uploaded_at") or event.get("extracted_at")

        sort_dt = _parse_any_datetime(event_at_raw) or _parse_any_datetime(ingested_at_raw)
        if not sort_dt:
            sort_dt = datetime.min.replace(tzinfo=timezone.utc)

        chronology_items.append(
            {
                "event_id": event.get("event_id") or f"evt_{idx}",
                "title": event.get("title") or "Event",
                "description": event.get("description") or "",
                "event_type": event.get("event_type") or "unknown",
                "verified": bool(event.get("verified")),
                "confidence": float(event.get("confidence", 0.0) or 0.0),
                "source_document_id": source_document_id,
                "source_document_name": linked_doc.get("original_filename") or "Unknown document",
                "event_time_display": _display_datetime(event_at_raw),
                "document_time_display": _display_datetime(document_created_at_raw),
                "ingested_time_display": _display_datetime(ingested_at_raw),
                "sort_ts": sort_dt.timestamp(),
                "function_group": TIMELINE_FUNCTION_GROUP,
            }
        )

    chronology_items.sort(key=lambda item: item.get("sort_ts", 0.0))
    for index, item in enumerate(chronology_items, start=1):
        item["sequence"] = index

    return chronology_items
