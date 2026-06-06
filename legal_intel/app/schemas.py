# app/schemas.py
from datetime import date, datetime
from pydantic import BaseModel
from typing import List, Optional

class DocketBase(BaseModel):
    date: Optional[date]
    entry_type: Optional[str]
    description: Optional[str]
    document_url: Optional[str]

class Docket(DocketBase):
    id: int
    class Config:
        orm_mode = True

class CaseBase(BaseModel):
    court: Optional[str]
    case_number: Optional[str]
    case_title: Optional[str]
    case_type: Optional[str]
    filing_date: Optional[date]
    status: Optional[str]

class Case(CaseBase):
    id: int
    dockets: List[Docket] = []
    class Config:
        orm_mode = True

class AttorneyBase(BaseModel):
    name: str
    bar_number: str
    state: str

class Attorney(AttorneyBase):
    id: int
    class Config:
        orm_mode = True

class EntityBase(BaseModel):
    name: str
    type: Optional[str]

class Entity(EntityBase):
    id: int
    class Config:
        orm_mode = True

class PatternSummary(BaseModel):
    total_cases: int
    default_rate: float
    settlement_rate: float
    avg_time_to_first_motion_days: Optional[float]
    top_entities: List[str]
    court_distribution: dict
