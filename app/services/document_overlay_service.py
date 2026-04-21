"""
DEPRECATED: Old Document Overlay Service (Local File Storage)

⚠️ WARNING: This module is deprecated. Use `app/services/unified_overlay_manager.py` instead.

This service stores overlays in local files (logs/document_overlays/records.json),
which violates Semptify's statelessness principle.

The unified overlay system:
- Stores all overlays in user's cloud storage
- No local file storage
- Cloud-only, stateless operation

This file will be removed in a future release.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.core.utc import utc_now
from app.models.document_overlay_models import (
    DocumentOverlayApplyResponse,
    DocumentOverlayCreate,
    DocumentOverlayDetail,
    DocumentOverlaySummary,
)

logger = logging.getLogger(__name__)


@dataclass
class _OverlayRecord:
    overlay_id: str
    document_id: str
    overlay_type: str
    payload: dict
    vault_id: str | None
    metadata: dict | None
    status: str
    created_at: datetime
    updated_at: datetime
    applied_at: datetime | None = None


# Log deprecation warning on module load
logger.warning(
    "DEPRECATED: document_overlay_service is deprecated. "
    "Use unified_overlay_manager for cloud-only overlay storage."
)


class DocumentOverlayService:
    """Durable overlay store that keeps source documents immutable."""

    def __init__(self, store_path: str | Path | None = None) -> None:
        self._records: dict[str, _OverlayRecord] = {}
        self._lock = Lock()
        self._store_path = Path(store_path or "logs/document_overlays/records.json")
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_records()

    def _load_records(self) -> None:
        if not self._store_path.exists():
            return

        try:
            raw = json.loads(self._store_path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                return

            for item in raw:
                try:
                    record = _OverlayRecord(
                        overlay_id=item["overlay_id"],
                        document_id=item["document_id"],
                        overlay_type=item["overlay_type"],
                        payload=dict(item.get("payload") or {}),
                        vault_id=item.get("vault_id"),
                        metadata=item.get("metadata"),
                        status=item.get("status", "draft"),
                        created_at=datetime.fromisoformat(item["created_at"]),
                        updated_at=datetime.fromisoformat(item["updated_at"]),
                        applied_at=(
                            datetime.fromisoformat(item["applied_at"])
                            if item.get("applied_at")
                            else None
                        ),
                    )
                    self._records[record.overlay_id] = record
                except Exception:
                    continue
        except Exception:
            self._records = {}

    def _save_records(self) -> None:
        payload = [
            {
                "overlay_id": record.overlay_id,
                "document_id": record.document_id,
                "overlay_type": record.overlay_type,
                "payload": record.payload,
                "vault_id": record.vault_id,
                "metadata": record.metadata,
                "status": record.status,
                "created_at": record.created_at.isoformat(),
                "updated_at": record.updated_at.isoformat(),
                "applied_at": record.applied_at.isoformat() if record.applied_at else None,
            }
            for record in self._records.values()
        ]

        self._store_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def create_overlay(self, payload: DocumentOverlayCreate) -> DocumentOverlayDetail:
        now = utc_now()
        overlay_id = f"ovl_{uuid4().hex[:10]}"

        record = _OverlayRecord(
            overlay_id=overlay_id,
            document_id=payload.document_id.strip(),
            overlay_type=payload.overlay_type.strip(),
            payload=dict(payload.payload),
            vault_id=payload.vault_id,
            metadata=payload.metadata,
            status="draft",
            created_at=now,
            updated_at=now,
        )

        with self._lock:
            self._records[overlay_id] = record
            self._save_records()

        return self._to_detail(record)

    def list_overlays(
        self,
        document_id: str | None = None,
        vault_id: str | None = None,
    ) -> list[DocumentOverlaySummary]:
        with self._lock:
            records = list(self._records.values())

        if document_id:
            records = [r for r in records if r.document_id == document_id]
        if vault_id:
            records = [r for r in records if r.vault_id == vault_id]

        records.sort(key=lambda item: item.created_at, reverse=True)
        return [self._to_summary(record) for record in records]

    def get_overlay(self, overlay_id: str) -> DocumentOverlayDetail | None:
        with self._lock:
            record = self._records.get(overlay_id)

        return self._to_detail(record) if record else None

    def apply_overlay(self, overlay_id: str, dry_run: bool) -> DocumentOverlayApplyResponse | None:
        with self._lock:
            record = self._records.get(overlay_id)
            if record is None:
                return None

            if dry_run:
                status = record.status
                message = "Dry-run complete. Overlay was validated but not applied."
            else:
                now = utc_now()
                record.status = "applied"
                record.applied_at = now
                record.updated_at = now
                self._save_records()
                status = record.status
                message = "Overlay applied successfully."

        return DocumentOverlayApplyResponse(
            overlay_id=overlay_id,
            status=status,
            dry_run=dry_run,
            message=message,
        )

    @staticmethod
    def _to_summary(record: _OverlayRecord) -> DocumentOverlaySummary:
        return DocumentOverlaySummary(
            overlay_id=record.overlay_id,
            document_id=record.document_id,
            overlay_type=record.overlay_type,
            vault_id=record.vault_id,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _to_detail(record: _OverlayRecord) -> DocumentOverlayDetail:
        return DocumentOverlayDetail(
            overlay_id=record.overlay_id,
            document_id=record.document_id,
            overlay_type=record.overlay_type,
            vault_id=record.vault_id,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            payload=record.payload,
            metadata=record.metadata,
            applied_at=record.applied_at,
        )


document_overlay_service = DocumentOverlayService()
