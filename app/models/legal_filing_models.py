import logging
from datetime import date

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class LegalCase(BaseModel):
    case_id: str
    tenant_name: str
    landlord_name: str
    address: str
    status: str = "draft"
    due_date: date | None = None
    notes: str | None = None


class EvidenceItem(BaseModel):
    item_id: str
    case_id: str
    description: str
    collected_on: date | None = None
    tags: list[str] = []
    vault_id: str | None = None
    overlay_record_ids: list[str] = []
    extracted_data: dict | None = None
