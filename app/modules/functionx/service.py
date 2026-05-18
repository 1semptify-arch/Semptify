from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from threading import Lock
from app.core.id_gen import make_id

from app.core.utc import utc_now
from app.models.functionx_models import (
    FunctionXActionSetCreate,
    FunctionXActionSetDetail,
    FunctionXActionSetSummary,
    FunctionXExecuteResponse,
)


@dataclass
class _ActionSetRecord:
    set_id: str
    name: str
    actions: list[str]
    metadata: dict | None
    status: str
    created_at: datetime
    last_executed_at: datetime | None = None


class FunctionXService:
    """In-memory service for FunctionX action-set planning and execution."""

    def __init__(self) -> None:
        self._records: dict[str, _ActionSetRecord] = {}
        self._lock = Lock()
        self._store_path = Path("logs/functionx/action_sets.json")
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
                    record = _ActionSetRecord(
                        set_id=item["set_id"],
                        name=item["name"],
                        actions=list(item.get("actions", [])),
                        metadata=item.get("metadata"),
                        status=item.get("status", "planned"),
                        created_at=datetime.fromisoformat(item["created_at"]),
                        last_executed_at=(
                            datetime.fromisoformat(item["last_executed_at"])
                            if item.get("last_executed_at")
                            else None
                        ),
                    )
                    self._records[record.set_id] = record
                except Exception:
                    continue
        except Exception:
            # Corrupt store should not break app startup.
            self._records = {}

    def _save_records(self) -> None:
        payload = [
            {
                "set_id": record.set_id,
                "name": record.name,
                "actions": record.actions,
                "metadata": record.metadata,
                "status": record.status,
                "created_at": record.created_at.isoformat(),
                "last_executed_at": (
                    record.last_executed_at.isoformat()
                    if record.last_executed_at is not None
                    else None
                ),
            }
            for record in self._records.values()
        ]
        self._store_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def create_action_set(self, payload: FunctionXActionSetCreate) -> FunctionXActionSetDetail:
        now = utc_now()
        set_id = make_id("fx")
        record = _ActionSetRecord(
            set_id=set_id,
            name=payload.name.strip(),
            actions=[a.strip() for a in payload.actions if a.strip()],
            metadata=payload.metadata,
            status="planned",
            created_at=now,
        )
        if not record.actions:
            raise ValueError("actions must contain at least one non-empty item")

        with self._lock:
            self._records[set_id] = record
            self._save_records()

        return self._to_detail(record)

    def list_action_sets(self) -> list[FunctionXActionSetSummary]:
        with self._lock:
            records = list(self._records.values())

        records.sort(key=lambda item: item.created_at, reverse=True)
        return [self._to_summary(record) for record in records]

    def get_action_set(self, set_id: str) -> FunctionXActionSetDetail | None:
        with self._lock:
            record = self._records.get(set_id)

        if record is None:
            return None
        return self._to_detail(record)

    def execute_action_set(self, set_id: str, dry_run: bool) -> FunctionXExecuteResponse | None:
        with self._lock:
            record = self._records.get(set_id)
            if record is None:
                return None

            if dry_run:
                status = "planned"
                message = "Dry-run complete. No persistent state changes were made."
            else:
                record.status = "executed"
                record.last_executed_at = utc_now()
                self._save_records()
                status = record.status
                message = "Action set executed successfully."

            processed_actions = len(record.actions)

        return FunctionXExecuteResponse(
            set_id=set_id,
            status=status,
            processed_actions=processed_actions,
            dry_run=dry_run,
            message=message,
        )

    @staticmethod
    def _to_summary(record: _ActionSetRecord) -> FunctionXActionSetSummary:
        return FunctionXActionSetSummary(
            set_id=record.set_id,
            name=record.name,
            status=record.status,
            actions_count=len(record.actions),
            created_at=record.created_at,
        )

    @staticmethod
    def _to_detail(record: _ActionSetRecord) -> FunctionXActionSetDetail:
        return FunctionXActionSetDetail(
            set_id=record.set_id,
            name=record.name,
            status=record.status,
            actions_count=len(record.actions),
            created_at=record.created_at,
            actions=record.actions,
            metadata=record.metadata,
            last_executed_at=record.last_executed_at,
        )


functionx_service = FunctionXService()
