
from typing import List
from pathlib import Path
import json
from datetime import date

from app.models.legal_filing_models import LegalCase

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "legal_filings"
EVIDENCE_DIR = DATA_DIR / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


def _case_file(case_id: str) -> Path:
    return DATA_DIR / f"case_{case_id}.json"


def _evidence_file(case_id: str) -> Path:
    return EVIDENCE_DIR / f"case_{case_id}_evidence.json"


def save_case(case: LegalCase) -> LegalCase:
    p = _case_file(case.case_id)
    p.write_text(case.model_dump_json(), encoding='utf-8')
    return case


def save_evidence(case_id: str, evidence) -> dict:
    p = _evidence_file(case_id)
    entries = []
    if p.exists():
        try:
            entries = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            entries = []
    entries.append(evidence.model_dump())
    p.write_text(json.dumps(entries, default=str), encoding='utf-8')
    return evidence.model_dump()


def load_case(case_id: str) -> LegalCase:
    p = _case_file(case_id)
    if not p.exists():
        raise FileNotFoundError(f"Case {case_id} not found")
    return LegalCase.model_validate_json(p.read_text(encoding='utf-8'))


def list_cases() -> List[LegalCase]:
    cases = []
    for f in DATA_DIR.glob('case_*.json'):
        try:
            cases.append(LegalCase.model_validate_json(f.read_text(encoding='utf-8')))
        except Exception:
            continue
    return cases


def list_evidence(case_id: str) -> list:
    p = _evidence_file(case_id)
    if not p.exists():
        return []

    try:
        entries = json.loads(p.read_text(encoding='utf-8'))
        if not isinstance(entries, list):
            return []
        return entries
    except Exception:
        return []

