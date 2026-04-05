#!/usr/bin/env python3
"""Semptify Legal Filing Module Deployer (simple local writer)

Creates minimal legal filing module files and registers the router in app/main.py.
"""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"

# Dir structure
DIRS = [
    APP / "routers",
    APP / "models",
    APP / "services",
    APP / "modules",
    APP / "templates" / "legal",
    ROOT / "data" / "legal_filings",
    ROOT / "data" / "legal_filings" / "cases",
]

for d in DIRS:
    d.mkdir(parents=True, exist_ok=True)

# Models
models_path = APP / "models" / "legal_filing_models.py"
models_code = '''
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
'''
models_path.write_text(models_code, encoding='utf-8')

# Services
service_path = APP / "services" / "legal_filing_service.py"
service_code = '''
from typing import List
from pathlib import Path
import json
from datetime import date

from app.models.legal_filing_models import LegalCase

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "legal_filings"

def _case_file(case_id: str) -> Path:
    return DATA_DIR / f"case_{case_id}.json"


def save_case(case: LegalCase) -> LegalCase:
    p = _case_file(case.case_id)
    p.write_text(case.model_dump_json(), encoding='utf-8')
    return case


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
'''
service_path.write_text(service_code, encoding='utf-8')

# Router
router_path = APP / "routers" / "legal_filing.py"
router_code = '''
from fastapi import APIRouter, HTTPException
from app.models.legal_filing_models import LegalCase
from app.services.legal_filing_service import save_case, load_case, list_cases

router = APIRouter(prefix="/api/legal-filing", tags=["Legal Filing"])

@router.get("/cases")
def get_cases():
    return list_cases()

@router.get("/cases/{case_id}")
def get_case(case_id: str):
    try:
        return load_case(case_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")

@router.post("/cases")
def create_case(case: LegalCase):
    saved = save_case(case)
    return {"status": "created", "case": saved}
'''
router_path.write_text(router_code, encoding='utf-8')

# Module SDK (stub)
module_path = APP / "modules" / "legal_filing_module.py"
module_code = '''
from app.routers.legal_filing import router as legal_filing_router

# Placeholder for actual module integration with mesh/network.

def init_module(app):
    app.include_router(legal_filing_router, tags=["Legal Filing"])
'''
module_path.write_text(module_code, encoding='utf-8')

# Templates
advocate_template = APP / "templates" / "legal" / "advocate_dashboard.html"
advocate_template.write_text('<h1>Advocate Legal Filing Dashboard</h1>', encoding='utf-8')

housing_template = APP / "templates" / "legal" / "housing_manager_monitor.html"
housing_template.write_text('<h1>Housing Manager Legal Filing Monitor</h1>', encoding='utf-8')

# Seed basic cases
seed_cases = [
    {"case_id": "C001", "tenant_name": "Alice Tenant", "landlord_name": "Bob Landlord", "address": "123 Main St", "status": "draft"},
    {"case_id": "C002", "tenant_name": "Charlie Tenant", "landlord_name": "Delta Landlord", "address": "456 Oak Ave", "status": "draft"},
]

data_dir = ROOT / "data" / "legal_filings"
for c in seed_cases:
    (data_dir / f"case_{c['case_id']}.json").write_text(json.dumps(c, default=str), encoding='utf-8')

# Patch app/main.py

main_path = APP / "main.py"
main_text = main_path.read_text(encoding='utf-8')

import_marker = "from app.routers.legal_analysis import router as legal_analysis_router"
insert_import = "from app.routers.legal_filing import router as legal_filing_router"

if insert_import not in main_text:
    main_text = main_text.replace(import_marker, import_marker + "\n" + insert_import)

router_marker = "app.include_router(legal_analysis_router, tags=[\"Legal Analysis\"])"
insert_router = "    app.include_router(legal_filing_router, tags=[\"Legal Filing\"])"

if insert_router not in main_text:
    main_text = main_text.replace(router_marker, router_marker + "\n" + insert_router)

main_path.write_text(main_text, encoding='utf-8')

print('✅ Legal Filing Module deployed. Created minimal files, seeded cases, patched app/main.py.')
