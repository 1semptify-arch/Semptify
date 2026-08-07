# app/schemas.py
from datetime import date

from pydantic import BaseModel


class DocketBase(BaseModel):
    date: date | None
    entry_type: str | None
    description: str | None
    document_url: str | None


class Docket(DocketBase):
    id: int

    class Config:
        orm_mode = True


class CaseBase(BaseModel):
    court: str | None
    case_number: str | None
    case_title: str | None
    case_type: str | None
    filing_date: date | None
    status: str | None


class Case(CaseBase):
    id: int
    dockets: list[Docket] = []

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
    type: str | None


class Entity(EntityBase):
    id: int

    class Config:
        orm_mode = True


class PatternSummary(BaseModel):
    total_cases: int
    default_rate: float
    settlement_rate: float
    avg_time_to_first_motion_days: float | None
    top_entities: list[str]
    court_distribution: dict
