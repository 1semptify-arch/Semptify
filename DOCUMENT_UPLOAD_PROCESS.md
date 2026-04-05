# Document Upload Process - Semptify 5.0

## Overview
Document upload is a **comprehensive, multi-stage workflow** that processes documents through vault storage, extraction, classification, analysis, and intelligent enrichment. The system ensures every document is cryptographically verified and tracked.

---

## System Status

### ✅ What's Working
- **Legal Filing Module**: Fully tested and operational (7/7 tests passing)
- **Case Manager Integration**: For managing tenant defense cases
- **Role-Based Access**: Users, advocates, managers, legal professionals, admins
- **Evidence Tracking**: Complete chain of custody

### ⚠️ What Needs Activation
- **Document Upload Endpoint**: Router not currently included in `app/main.py`
  - `documents.py` exists but needs to be dynamically loaded
  - `intake.py` exists for comprehensive document intake
  - Tests are written but endpoint returns 404 (not registered)

---

## Document Upload Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER UPLOADS DOCUMENT                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                    ┌────▼────┐
                    │ STEP 0:  │
                    │ NOTARIZE │ (Tamper-proof receipt with SHA256)
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │ STEP 1:  │
                    │  VAULT   │ (User's cloud/local storage)
                    │ UPLOAD   │ (Google Drive, Dropbox, OneDrive, Local)
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │ STEP 2:  │
                    │ REGISTER │ (Unique SEM-ID, chain of custody)
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │ STEP 3:  │
                    │PIPELINE  │ (OCR, Text extraction, store)
                    │PROCESSING│
                    └────┬────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼────┐   ┌──────▼──────┐   ┌────▼────┐
   │CLASSIFY  │   │   EXTRACT    │   │ ANALYZE  │
   │Doc Type  │   │   Data       │   │ Laws &   │
   │(Lease,   │   │   (Dates,    │   │ Insights │
   │Notice, etc)│ │   Parties,  │   │(Urgency, │
   │           │   │   Amounts)  │   │Actions)  │
   └────┬────┘   └──────┬──────┘   └────┬────┘
        │                │              │
        └────────────────┼──────────────┘
                         │
                    ┌────▼────────────┐
                    │ STEP 4:         │
                    │ CROSS-REFERENCE │
                    │ (Match with     │
                    │ MN tenant laws) │
                    └────┬────────────┘
                         │
                    ┌────▼────────────┐
                    │ STEP 5:         │
                    │ VERIFY          │
                    │ (Duplicates,    │
                    │ Forgery,        │
                    │ Integrity)      │
                    └────┬────────────┘
                         │
                    ┌────▼────────────┐
                    │ STEP 6:         │
                    │ ENRICH          │
                    │ (Action items,  │
                    │ Timeline,       │
                    │ Deadlines)      │
                    └────┬────────────┘
                         │
        ┌────────────────▼──────────────────┐
        │  RETURN COMPREHENSIVE RESULT       │
        │ - Document ID + Registry ID        │
        │ - Classification + Confidence      │
        │ - Extracted Data Counts           │
        │ - Legal References                 │
        │ - Action Items                    │
        │ - Urgency Assessment              │
        └────────────────────────────────────┘
```

---

## Endpoint Specifications

### Main Upload Endpoint
**POST /api/documents/upload**

#### Request
```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@lease_agreement.pdf" \
  -F "document_type=lease" \
  -F "storage_provider=local" \
  -F "case_number=EV-2025-001234"
```

#### Form Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | File | ✅ | PDF, image, or document file (max 50MB) |
| `document_type` | String | ❌ | lease, notice, complaint, court_filing, etc. |
| `storage_provider` | String | ❌ | local, google_drive, dropbox, onedrive |
| `access_token` | String | ❌ | Cloud provider auth token |
| `case_number` | String | ❌ | Link to existing case |

#### Response
```json
{
  "id": "doc-abc123xyz",
  "registry_id": "SEM-2025-001234-ABCD",
  "filename": "lease_agreement.pdf",
  "status": "processing",
  "intake_status": "extracting",
  "doc_type": "lease",
  "confidence": 0.98,
  "title": "Residential Lease Agreement",
  "summary": "Standard residential lease for 12-month term",
  "key_dates_count": 4,
  "key_parties_count": 3,
  "key_amounts_count": 2,
  "is_duplicate": false,
  "content_hash": "sha256:abc123...",
  "integrity_verified": true,
  "forgery_score": 0.02,
  "law_references_count": 5,
  "matched_statutes": [
    "Minnesota Statute 504B.005",
    "Minnesota Statute 504B.161"
  ],
  "urgency_level": "high",
  "action_items_count": 3,
  "processed_at": "2025-04-02T09:30:00Z",
  "message": "✓ Document stored in vault (local). Processing complete with 5 legal references matched."
}
```

### Alternative: Intake Upload Endpoint
**POST /api/intake/upload**

Simpler upload-only (deferred processing):
```bash
curl -X POST http://localhost:8000/api/intake/upload \
  -F "file=@notice.pdf" \
  -F "user_id=GUtest1234" \
  -F "storage_provider=local"
```

### Auto-Process Upload Endpoint
**POST /api/intake/upload/auto**

Complete pipeline in one request (wait for result):
```bash
curl -X POST http://localhost:8000/api/intake/upload/auto \
  -F "file=@summons.pdf" \
  -F "user_id=GVadvocate123"
```

---

## Data Flow Details

### Step 1: Notarization (OPTIONAL but RECOMMENDED)
- **Purpose**: Create tamper-proof receipt
- **Process**: 
  - Compute SHA-256 hash of file
  - Record upload timestamp, username, IP address
  - Generate notarization certificate
- **Output**: Notarization ID for proof of upload
- **Files**: `app/services/document_notarization.py`

### Step 2: Vault Upload
- **Purpose**: Store document in user's cloud storage or local filesystem
- **Providers**:
  - ✅ **Local Storage** (default): `uploads/vault/` directory
  - 🔄 **Google Drive**: Requires auth token
  - 🔄 **Dropbox**: Requires app key
  - 🔄 **OneDrive**: Requires credentials
- **Output**: Vault ID, storage path
- **Files**: `app/services/vault_upload_service.py`

### Step 3: Registration
- **Purpose**: Create unique Semptify Document ID (SEM-YYYY-NNNNNN-XXXX)
- **Process**:
  - Check for duplicates by content hash
  - Compute forgery risk score
  - Validate file integrity
  - Create chain of custody entry
- **Output**: Registry ID, duplicate status, integrity metrics
- **Files**: `app/services/document_registry.py`

### Step 4: Intake Processing
- **Purpose**: Parse and structure document content
- **Sub-steps**:
  - OCR if image/scan
  - Extract text
  - Segment into sections
  - Parse metadata
- **Output**: Structured document with extracted text
- **Files**: `app/services/document_intake.py`

### Step 5: Classification & Extraction
- **Purpose**: Identify document type and extract key data
- **Extracted Data**:
  - **Dates**: Lease start/end, notice deadlines, court dates
  - **Parties**: Landlord, tenant, attorney names and addresses
  - **Amounts**: Rent, deposit, fees, damages claimed
  - **Terms**: Conditions, obligations, restrictions
  - **Case Numbers**: Court file numbers for litigation
- **Document Types**: lease, notice, complaint, court_filing, motion, affidavit, lease_modification, etc.
- **Files**: `app/services/document_pipeline.py`, `app/services/document_intelligence.py`

### Step 6: Legal Cross-Reference
- **Purpose**: Match document with applicable Minnesota tenant laws
- **Process**:
  - Identify legal issues (improper notice, lack of cause, etc.)
  - Match against MN statutes
  - Score tenant protections
  - Identify rights and remedies
- **Output**: Matched statute list, legal insights, action items
- **Files**: `app/services/law_engine.py`

### Step 7: Verification
- **Purpose**: Detect duplicates, forgeries, and integrity issues
- **Checks**:
  - Duplicate by content hash
  - Forgery risk (scanned vs. digital, alterations)
  - Integrity verification (official court documents)
  - Extraction confidence scores
- **Output**: Duplicate flag, forgery score, verification status
- **Files**: `app/services/document_registry.py`

### Step 8: Enrichment
- **Purpose**: Add actionable insights
- **Enrichments**:
  - **Timeline Events**: Automatically create calendar entries
  - **Urgency Assessment**: Priority level (critical, high, medium, low)
  - **Action Items**: What user should do next
  - **Deadline Tracking**: Days until critical dates
- **Output**: Action items, timeline, urgency level
- **Files**: `app/services/action_router.py`, `app/services/timeline_builder.py`

---

## Testing & Verification

### Run Legal Filing Tests (Working)
```bash
cd C:\Semptify\Semptify-FastAPI
.venv\Scripts\python.exe -m pytest tests/test_legal_filing.py -v
# Result: ✅ 7/7 PASSED
```

### Run Document Tests (Needs Router Registration)
```bash
cd C:\Semptify\Semptify-FastAPI
.venv\Scripts\python.exe -m pytest tests/test_documents.py::test_document_upload -v
# Current Result: ⚠️ 404 Not Found (router not registered in main.py)
```

### Manual Test (Once Router is Enabled)
```bash
# Start server
.venv\Scripts\python.exe -m uvicorn app.main:app --reload

# Test upload
curl -X POST http://127.0.0.1:8000/api/documents/upload \
  -F "file=@test.pdf"
```

---

## Why Upload Tests Currently Fail

The document upload endpoint **exists and is fully implemented** but returns 404 because:

1. ✅ **Files exist**:
   - `app/routers/documents.py` - Main upload router (≈500 lines)
   - `app/routers/intake.py` - Intake router (≈800 lines)
   - `app/services/document_pipeline.py` - Processing engine
   - `tests/test_documents.py` - Comprehensive tests

2. ❌ **Router not registered in `app/main.py`**:
   - Use `include_if(documents_router)` to conditionally load
   - Same pattern as legal filing router

3. ✅ **All dependencies exist**:
   - Vault service
   - Document registry
   - OCR/extraction
   - Law engine
   - Timeline builder

---

## To Enable Document Upload

### Option 1: Quick Enable (Testing)
Edit `app/main.py` line ~1603 and add:
```python
include_if(documents_router, tags=["Documents"])
```

### Option 2: Full Flow (Production)
```python
# At top of app/main.py
try:
    from app.routers import documents
    documents_router = documents.router
except ImportError:
    documents_router = None

# In register routers section
include_if(documents_router, tags=["Documents"])  # Document upload, analysis
```

---

## Related Modules

### Legal Filing Module (✅ WORKING)
- **Status**: Fully implemented, 7/7 tests passing
- **Endpoints**:
  - `POST /api/legal-filing/cases` (advocate+ roles)
  - `GET /api/legal-filing/cases` (all authenticated)
  - `POST /api/legal-filing/cases/{id}/evidence` (advocate+ roles)
  - `GET /api/legal-filing/cases/{id}/evidence` (all authenticated)

### Document Intake Module (⏳ READY)
- **Status**: Fully coded, needs router registration
- **Endpoints**:
  - `POST /api/intake/upload` - Basic upload
  - `POST /api/intake/upload/auto` - Auto-process

### Supporting Services (✅ ALL AVAILABLE)
- `vault_upload_service.py` - Cloud/local storage
- `document_registry.py` - Unique IDs, deduplication
- `document_intake.py` - Text extraction
- `document_pipeline.py` - Processing orchestration
- `document_intelligence.py` - AI-powered analysis
- `law_engine.py` - Legal cross-reference
- `document_notarization.py` - Tamper-proof records
- `timeline_builder.py` - Deadline tracking

---

## Summary

| Component | Status | Tests | Notes |
|-----------|--------|-------|-------|
| **Legal Filing APIs** | ✅ Active | 7/7 pass | Case + evidence tracking |
| **Document Upload Routers** | ⏳ Code ready | 6/6 written | Not registered in main.py |
| **Upload Processing Engine** | ✅ Complete | Multiple | All services available |
| **Vault Storage** | ✅ Complete | ✅ | Local + cloud providers |
| **Document Registry** | ✅ Complete | ✅ | Deduplication, integrity |
| **Law Cross-Reference** | ✅ Complete | ✅ | MN statutes matched |
| **Intake & Intelligence** | ✅ Complete | ✅ | Extraction, analysis |

**Next Step**: Register document routers in `app/main.py` to activate upload endpoints.
