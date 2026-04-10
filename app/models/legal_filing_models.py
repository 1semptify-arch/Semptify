
from pydantic import BaseModel
from datetime import date
from typing import List, Optional

class LegalCase(BaseModel):
    case_id: str
    tenant_name: str
    landlord_name: str
    address: str
    status: str = "draft"
    due_date: Optional[date] = None
    notes: Optional[str] = None

class EvidenceItem(BaseModel):
    item_id: str
    case_id: str
    description: str
    collected_on: Optional[date] = None
    tags: List[str] = []
    vault_id: Optional[str] = None
    overlay_record_ids: List[str] = []
    extracted_data: Optional[dict] = None
