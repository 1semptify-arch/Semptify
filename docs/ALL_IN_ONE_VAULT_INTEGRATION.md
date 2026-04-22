# ALL-IN-ONE Unified Evidence Vault — Integration Guide

**Status:** ✅ Implemented  
**Version:** Semptify 5.0  
**Date:** April 21, 2026

---

## Terminology

- **The Vault** = Cloud storage (`Semptify5.0/Vault/` in user's Google Drive)
- **vault_items table** = Metadata index that describes what's in the vault
- **ALL-IN-ONE system** = Three-timestamp metadata layer on top of the existing vault

---

## Overview

The ALL-IN-ONE metadata layer is now fully integrated into Semptify 5.0. It provides deep search, audit trails, and timeline views for the **cloud vault** (which remains the source of truth). Features:

- **Three-timestamp model** (event_time, record_time, semptify_entry_time)
- **Data contract enforcement** (metadata preservation)
- **Deep search** via PostgreSQL JSONB GIN indexes
- **Incident grouping** for organizing related evidence
- **Complete audit trail** with before/after states

---

## Quick Start

### 1. Run the Migration

```bash
# Activate virtual environment
.\venv311\Scripts\activate

# Run the migration
cd c:\Semptify\Semptify-FastAPI
alembic upgrade a1b2c3d4e5f6
```

### 2. Verify Installation

Start the server and check the logs:
```
🏛️ ALL-IN-ONE Vault router connected - Unified evidence vault with three-timestamp model active
```

### 3. Test the API

```bash
# Ingest a vault item
curl -X POST http://localhost:8000/vault/items \
  -H "Content-Type: application/json" \
  -H "Cookie: se_user=YOUR_USER_ID" \
  -d '{
    "item_type": "notice",
    "event_time": "2026-01-15T10:30:00Z",
    "record_time": "2026-01-15T10:30:00Z",
    "metadata": {
      "notice_type": "pay_or_quit",
      "amount_due": 1500.00
    },
    "title": "3-Day Pay or Quit Notice",
    "severity": "critical"
  }'
```

---

## API Endpoints

### Vault Items

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/vault/items` | Ingest new evidence |
| GET | `/vault/items` | Search vault with filtering |
| POST | `/vault/items/search` | Advanced search (POST body) |
| GET | `/vault/items/{item_id}` | Get single item |
| PUT | `/vault/items/{item_id}` | Update item (immutable fields protected) |
| DELETE | `/vault/items/{item_id}` | Delete item (with audit log) |

### Timeline Views

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/vault/timeline` | Timeline view with three-timestamp ordering |

### Incidents

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/vault/incidents` | Create incident/case |
| GET | `/vault/incidents` | List incidents |
| GET | `/vault/incidents/{id}` | Get incident with item count |
| GET | `/vault/incidents/{id}/timeline` | Incident timeline |

### Deep Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/vault/search/metadata` | Search by metadata field |
| GET | `/vault/search/location` | Geographic search |

---

## Three-Timestamp Model

Every vault item stores three timestamps:

| Timestamp | Meaning | Usage |
|-----------|---------|-------|
| `event_time` | When the event actually occurred | Factual timeline ordering |
| `record_time` | When evidence was created/recorded | Document provenance |
| `semptify_entry_time` | When added to Semptify | System ingestion time |

### Query by Different Timelines

```bash
# Order by when events occurred
curl "/vault/timeline?timeline_mode=event_time"

# Order by when evidence was created
curl "/vault/timeline?timeline_mode=record_time"

# Order by when added to Semptify
curl "/vault/timeline?timeline_mode=semptify_entry_time"
```

---

## Data Contract

### Required Fields

```json
{
  "item_type": "string (required)",
  "event_time": "datetime (required)",
  "record_time": "datetime (required)",
  "metadata": "object (required, empty {} acceptable)"
}
```

### Rules

1. **Never discard metadata** — All extracted metadata is preserved
2. **Never flatten metadata** — Nested JSON structures maintained
3. **Never overwrite timestamps** — Three timestamps are immutable
4. **Preserve nested JSON** — Deep structures stored in JSONB
5. **If unknown → set null** — Missing values use null, not defaults

---

## Deep Search Examples

### Search Metadata

```bash
# Find all items with landlord = "ABC Management"
curl "/vault/search/metadata?field=landlord&value=ABC%20Management"
```

### Location Search

```bash
# Find items near coordinates
curl "/vault/search/location?lat=44.9778&lon=-93.2650&radius=1000"
```

### Combined Filters

```bash
# Complex search
curl "/vault/items?item_type=notice&severity=critical&date_from=2026-01-01&timeline_mode=event_time"
```

---

## Incident Grouping

Incidents organize related evidence into coherent case narratives.

### Create Incident

```bash
curl -X POST http://localhost:8000/vault/incidents \
  -H "Content-Type: application/json" \
  -H "Cookie: se_user=YOUR_USER_ID" \
  -d '{
    "title": "Habitability Violations - Unit 4B",
    "description": "Ongoing heating and plumbing issues",
    "incident_type": "habitability",
    "severity": "high"
  }'
```

### Link Items to Incident

```bash
curl -X PUT http://localhost:8000/vault/items/123 \
  -H "Content-Type: application/json" \
  -H "Cookie: se_user=YOUR_USER_ID" \
  -d '{
    "related_incident_id": 456
  }'
```

### Get Incident Timeline

```bash
curl "/vault/incidents/456/timeline?timeline_mode=event_time"
```

---

## Architecture

### Models

| File | Model | Purpose |
|------|-------|---------|
| `app/models/models.py` | `VaultItem` | Unified evidence storage |
| `app/models/models.py` | `Incident` | Case grouping |
| `app/models/models.py` | `VaultAuditLog` | Change tracking |

### Services

| File | Service | Purpose |
|------|---------|---------|
| `app/services/vault_ingestion.py` | `VaultIngestionService` | Data contract enforcement |
| `app/services/vault_search.py` | `VaultSearchService` | Deep search & timeline |

### API Router

| File | Router | Prefix |
|------|--------|--------|
| `app/routers/vault_all_in_one.py` | `vault_all_in_one` | `/vault` |

### Migration

| File | Revision | Tables |
|------|----------|--------|
| `alembic/versions/a1b2c3d4e5f6_add_all_in_one_vault_tables.py` | a1b2c3d4e5f6 | vault_items, incidents, vault_audit_logs |

---

## Database Schema

### vault_items Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| item_id | SERIAL | PK | Auto-increment ID |
| user_id | VARCHAR(24) | FK, Index | User ownership |
| **event_time** | TIMESTAMPTZ | NOT NULL, Index | Factual occurrence |
| **record_time** | TIMESTAMPTZ | NOT NULL, Index | Evidence creation |
| **semptify_entry_time** | TIMESTAMPTZ | NOT NULL, Index | System ingestion |
| item_type | VARCHAR(50) | NOT NULL, Index | Document type |
| folder | VARCHAR(255) | Nullable | Virtual folder |
| tags | JSONB | Nullable, GIN | Searchable tags |
| related_incident_id | INTEGER | FK, Index | Incident grouping |
| source | VARCHAR(100) | Nullable | Evidence source |
| severity | VARCHAR(20) | Nullable | critical/high/normal/low |
| status | VARCHAR(20) | Nullable | pending/verified/disputed/archived |
| location_data | JSONB | Nullable, GIN | GPS, coordinates |
| metadata | JSONB | NOT NULL, GIN | Preserved metadata |
| file_path | VARCHAR(500) | Nullable | Cloud storage path |
| title | VARCHAR(255) | Nullable | Display title |
| summary | TEXT | Nullable | Description |

### Indexes

| Index | Type | Purpose |
|-------|------|---------|
| idx_vault_metadata_gin | GIN | Deep metadata search |
| idx_vault_location_gin | GIN | Location search |
| idx_vault_tags_gin | GIN | Tag filtering |
| idx_vault_event_time | BTREE | Timeline ordering |
| idx_vault_record_time | BTREE | Record timeline |
| idx_vault_entry_time | BTREE | Ingestion timeline |

---

## Module Contracts

The vault services register with the module contract system:

```python
# vault_ingestion.py
FunctionGroupContract(
    module="vault",
    group_name="vault_ingestion",
    title="Vault Ingestion Service",
    description="Ingest evidence with data contract enforcement",
    inputs=("user_id", "item_type", "event_time", "record_time", "metadata"),
    outputs=("item_id", "audit_log_id"),
    deterministic=True,
)

# vault_search.py
FunctionGroupContract(
    module="vault",
    group_name="vault_search",
    title="Vault Search Service",
    description="Deep search and timeline queries",
    inputs=("user_id", "search_criteria", "timeline_mode"),
    outputs=("items", "total_count", "timeline_sequence"),
    deterministic=True,
)
```

---

## Integration with Existing Systems

### Timeline Chronology

The existing `app/services/timeline_chronology.py` continues to work with cloud-based timeline events (`Semptify5.0/Vault/timeline/events.json`). The ALL-IN-ONE metadata layer provides fast PostgreSQL-backed queries for:

- Faster queries for large datasets
- Complex filtering and aggregation
- Audit trail requirements

**Important**: The cloud vault remains the source of truth. The PostgreSQL tables are a metadata index.

### Overlay System

Document overlays are stored in the vault at `Semptify5.0/Vault/.overlay/`. The ALL-IN-ONE metadata layer indexes overlay metadata for:

- Fast search across overlays
- Incident grouping for case organization
- Audit trails for compliance

### Cloud Storage Paths

The vault uses canonical paths from `app/core/vault_paths.py`:

```python
VAULT_DOCUMENTS = "Semptify5.0/Vault/documents"
VAULT_OVERLAY = "Semptify5.0/Vault/.overlay"
VAULT_TIMELINE = "Semptify5.0/Vault/timeline"
```

---

## Best Practices

### 1. Always Provide All Three Timestamps

```python
# Good - complete timestamp information
request = IngestionRequest(
    event_time=notice_date,        # When notice was served
    record_time=document_date,     # When document was created
    metadata={"source": "upload"},  # Semptify_entry_time auto-set
)
```

### 2. Preserve Raw Metadata

```python
# Good - preserve everything
metadata = {
    "exif": raw_exif_data,
    "extracted_text": ocr_result,
    "user_tags": user_input,
    "confidence_scores": model_output,
}
```

### 3. Use Incidents for Case Organization

```python
# Create incident for case
curl -X POST /vault/incidents -d '{"title": "Case 2026-001", "incident_type": "eviction"}'

# Link all related items
curl -X PUT /vault/items/1 -d '{"related_incident_id": 1}'
curl -X PUT /vault/items/2 -d '{"related_incident_id": 1}'
curl -X PUT /vault/items/3 -d '{"related_incident_id": 1}'

# Get complete case timeline
curl /vault/incidents/1/timeline
```

### 4. Leverage Deep Search

```python
# Search by any metadata field
results = await search_service.deep_metadata_search(
    user_id=user_id,
    metadata_field="landlord",
    value="ABC Management"
)
```

---

## Compliance Notes

- **GDPR**: Audit logs track all access and modifications
- **Evidence Integrity**: Three timestamps provide complete provenance chain
- **Audit Trail**: Every change logged with before/after states
- **Immutable Core**: Event time, record time, and entry time are immutable

---

## Troubleshooting

### Migration Failed

```bash
# Check current revision
alembic current

# Check revision history
alembic history

# If needed, stamp to previous and retry
alembic stamp 81c36d8f2466
alembic upgrade a1b2c3d4e5f6
```

### JSONB Queries Slow

Verify GIN indexes are created:
```sql
SELECT indexname FROM pg_indexes WHERE tablename = 'vault_items';
-- Should show: idx_vault_metadata_gin, idx_vault_location_gin, idx_vault_tags_gin
```

### Timestamp Errors

Ensure all timestamps are timezone-aware:
```python
from datetime import datetime, timezone

# Good - UTC timezone
event_time = datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc)

# Bad - no timezone (will be auto-converted to UTC)
event_time = datetime(2026, 1, 15, 10, 30)
```

---

## Next Steps

1. **Integrate with document upload flow** — Auto-ingest uploaded documents
2. **Add timeline sync** — Mirror cloud timeline events to vault_items
3. **Build incident UI** — Frontend for case organization
4. **Implement batch ingestion** — Bulk import from existing documents
5. **Add reporting** — Export incident timelines for legal proceedings

---

*The ALL-IN-ONE Unified Evidence Vault is now active and ready for production use.*
