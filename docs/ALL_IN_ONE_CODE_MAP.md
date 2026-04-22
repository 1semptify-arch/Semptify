# ALL-IN-ONE Vault — Code Map & Architecture Integration

**Visual guide to how the metadata layer fits on top of Semptify's cloud vault.**

> **Terminology**: The **Vault** = Cloud storage (`Semptify5.0/Vault/`).  
> The `vault_items` table is a **metadata index** that describes vault contents.

---

## High-Level Architecture Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SEMPTIFY 5.0 ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        API LAYER (Routers)                           │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │    │
│  │  │   /vault     │  │ /timeline    │  │     /documents         │   │    │
│  │  │ (ALL-IN-ONE) │  │ (existing)   │  │   (existing)           │   │    │
│  │  │              │  │              │  │                        │   │    │
│  │  │ • POST items │  │ Cloud events │  │ Upload & storage       │   │    │
│  │  │ • GET search │  │ Chronology   │  │                        │   │    │
│  │  │ • PUT update │  │ 3 timestamps │  │                        │   │    │
│  │  │ • DELETE     │  │              │  │                        │   │    │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘   │    │
│  │           │                 │                      │                │    │
│  └───────────┼─────────────────┼──────────────────────┼────────────────┘    │
│              │                 │                      │                     │
│              ▼                 ▼                      ▼                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      SERVICE LAYER                                  │    │
│  │  ┌────────────────────┐  ┌──────────────────┐  ┌──────────────┐   │    │
│  │  │ VaultIngestion     │  │ VaultSearch        │  │ TimelineChro │   │    │
│  │  │ Service            │  │ Service            │  │ nology       │   │    │
│  │  │                    │  │                    │  │              │   │    │
│  │  │ • Data contract    │  │ • Deep search      │  │ • Cloud      │   │    │
│  │  │ • 3 timestamps     │  │ • JSONB GIN        │  │   timeline   │   │    │
│  │  │ • Audit logging    │  │ • Timeline modes   │  │ • Events     │   │    │
│  │  └────────────────────┘  └──────────────────┘  └──────────────┘   │    │
│  │           │                      │                      │         │    │
│  └───────────┼──────────────────────┼──────────────────────┼─────────┘    │
│              │                      │                      │              │
│              ▼                      ▼                      ▼              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      MODEL LAYER (SQLAlchemy)                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐   │   │
│  │  │ VaultItem   │  │  Incident   │  │ VaultAudit  │  │ Timeline   │   │   │
│  │  │             │  │             │  │ Log         │  │ Event      │   │   │
│  │  │ • 3 ts      │  │ • Case grp  │  │ • Before    │  │ (existing) │   │   │
│  │  │ • JSONB     │  │ • Timeline  │  │ • After     │  │            │   │   │
│  │  │ • Metadata  │  │ • Metadata  │  │ • Immutable │  │            │   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘   │   │
│  │           │              │              │              │               │   │
│  └───────────┼──────────────┼──────────────┼──────────────┼───────────────┘   │
│              │              │              │              │                 │
│              ▼              ▼              ▼              ▼                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    DATABASE (PostgreSQL)                            │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │   │
│  │  │ vault_items │  │  incidents  │  │vault_audit  │  │  timeline  │ │   │
│  │  │             │  │             │  │   _logs     │  │  _events    │ │   │
│  │  │ + GIN idx   │  │             │  │             │  │            │ │   │
│  │  │ on metadata │  │             │  │             │  │            │ │   │
│  │  │ location    │  │             │  │             │  │            │ │   │
│  │  │ tags        │  │             │  │             │  │            │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Integration Points Map

### 1. Vault Ingestion → Existing Document Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOCUMENT UPLOAD FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User uploads document                                           │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────┐                                         │
│  │ /documents/upload   │ (existing)                              │
│  │                     │                                         │
│  │ Stores to:          │                                         │
│  │ Semptify5.0/        │                                         │
│  │   Vault/documents/  │                                         │
│  └─────────────────────┘                                         │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────┐     ┌─────────────────────────┐       │
│  │ Timeline Extraction │───▶ │ Semptify5.0/Vault/      │       │
│  │ (existing)          │     │   timeline/events.json  │       │
│  └─────────────────────┘     └─────────────────────────┘       │
│         │                                                        │
│         │ NEW: Auto-ingest to ALL-IN-ONE vault                   │
│         ▼                                                        │
│  ┌─────────────────────┐                                         │
│  │ VaultIngestionService│                                         │
│  │                     │                                         │
│  │ • event_time = doc  │                                         │
│  │   creation date     │                                         │
│  │ • record_time = doc │                                         │
│  │   upload time       │                                         │
│  │ • semptify_entry =  │                                         │
│  │   NOW()             │                                         │
│  │ • metadata = full   │                                         │
│  │   extraction data   │                                         │
│  └─────────────────────┘                                         │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────┐                                         │
│  │ PostgreSQL          │                                         │
│  │ vault_items table   │                                         │
│  └─────────────────────┘                                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Metadata Index → Vault (Cloud Storage)

```
┌─────────────────────────────────────────────────────────────────┐
│                    VAULT + METADATA INDEX LAYERS                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 THE VAULT (Cloud Storage)                │  │
│  │                 Source of Truth                         │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐ │  │
│  │  │ Documents   │    │  Overlays   │    │   Timeline   │ │  │
│  │  │             │    │             │    │   events.json│ │  │
│  │  │ /Vault/     │    │ /Vault/     │    │              │ │  │
│  │  │  documents/│    │  .overlay/  │    │              │ │  │
│  │  └─────────────┘    └─────────────┘    └──────────────┘ │  │
│  │         │                  │                  │          │  │
│  └─────────┼──────────────────┼──────────────────┼──────────┘  │
│            │                  │                  │               │
│            ▼                  ▼                  ▼               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              METADATA INDEX (PostgreSQL)                 │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │              vault_items table (points TO vault)    │  │  │
│  │  │  • file_path ────────▶ cloud document location    │  │  │
│  │  │  • metadata ─────────▶ extracted overlay data     │  │  │
│  │  │  • location_data ────▶ GPS from extraction        │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                         │                                │  │
│  │              ┌──────────┴──────────┐                     │  │
│  │              ▼                     ▼                     │  │
│  │  ┌──────────────────┐  ┌──────────────────┐              │  │
│  │  │ VaultSearch      │  │ OverlayManager   │              │  │
│  │  │ Service          │  │ (manages vault)  │              │  │
│  │  │                  │  │                  │              │  │
│  │  │ • Fast queries   │  │ • Reads/writes   │              │  │
│  │  │ • Deep search    │  │   vault files    │              │  │
│  │  │ • Timeline       │  │ • Registry       │              │  │
│  │  └──────────────────┘  └──────────────────┘              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Flow: Search index → Find file_path → Fetch from vault        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Timeline: Vault vs Metadata Index

```
┌─────────────────────────────────────────────────────────────────┐
│              TIMELINE DATA: Two Complementary Layers             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────┐    ┌─────────────────────────────┐│
│  │   VAULT TIMELINE        │    │   METADATA INDEX TIMELINE     ││
│  │   (Cloud - Source)      │    │   (PostgreSQL - Index)        ││
│  │                         │    │                                ││
│  │ • events.json in        │    │ • vault_items table            ││
│  │   cloud storage         │    │ • JSONB GIN indexes            ││
│  │ • The actual timeline   │    │ • Fast queryable index         ││
│  │ • Portable with user    │    │ • Deep metadata search         ││
│  │ • Survives DB reset     │    │ • Audit trail                  ││
│  │ • Cross-device sync     │    │ • Complex filtering            ││
│  │                         │    │                                ││
│  │ Best for:               │    │ Best for:                      ││
│  │ • Source of truth       │    │ • Fast queries                 ││
│  │ • Long-term storage     │    │ • Reporting                    ││
│  │ • User control          │    │ • Legal discovery              ││
│  └─────────────────────────┘    └─────────────────────────────┘│
│                              │                                   │
│                              │ Index syncs TO vault             │
│                              ▼                                   │
│                    ┌─────────────────────┐                       │
│                    │  vault_items keeps  │                       │
│                    │  file_path pointer  │                       │
│                    │  to cloud location  │                       │
│                    └─────────────────────┘                       │
│                                                                  │
│  IMPORTANT: vault_items.file_path points to Semptify5.0/Vault/  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Maps

### Vault Item Ingestion Flow

```
┌─────────────┐     ┌────────────────────────┐     ┌─────────────────┐
│   Client    │────▶│  POST /vault/items     │────▶│   Validation    │
│  Request    │     │  (vault_all_in_one.py) │     │  (Pydantic)     │
└─────────────┘     └────────────────────────┘     └────────┬────────┘
                                                          │
                    ┌─────────────────────────────────────┘
                    ▼
          ┌─────────────────────────┐
          │ VaultIngestionService   │
          │                         │
          │ 1. _validate_request()  │
          │    - Check 3 timestamps │
          │    - Check metadata     │
          │                         │
          │ 2. _preserve_metadata() │
          │    - Convert datetime   │
          │    - Serialize nested   │
          │    - Keep everything    │
          │                         │
          │ 3. Create VaultItem     │
          │ 4. Create AuditLog      │
          └───────────┬─────────────┘
                      │
                      ▼
          ┌─────────────────────────┐
          │     PostgreSQL            │
          │  ┌─────────────────┐      │
          │  │ INSERT vault_items    │      │
          │  │ INSERT vault_audit_logs│     │
          │  └─────────────────┘      │
          └─────────────────────────┘
                      │
                      ▼
          ┌─────────────────────────┐
          │    JSONB GIN Indexes    │
          │    Auto-updated         │
          │    for search           │
          └─────────────────────────┘
```

### Search Query Flow

```
┌─────────────┐     ┌────────────────────────┐
│   Client    │────▶│  GET /vault/items      │
│   Query     │     │  ?timeline_mode=       │
│             │     │    event_time           │
└─────────────┘     └───────────┬────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ SearchCriteria        │
                    │ (Pydantic model)      │
                    │                       │
                    │ • query (text)        │
                    │ • metadata_query      │
                    │ • timeline_mode       │
                    │ • date_from/to        │
                    │ • filters...          │
                    └───────────┬─────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ VaultSearchService    │
                    │                       │
                    │ _build_base_query()   │
                    │ _apply_text_search()  │
                    │ _apply_metadata_search()│
                    │ _apply_date_range()   │
                    │ _apply_sorting()      │
                    └───────────┬─────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │   SQL Generated     │
                    │                     │
                    │ SELECT * FROM       │
                    │   vault_items       │
                    │ WHERE user_id = ?   │
                    │   AND metadata::text│
                    │     ILIKE '%term%'  │
                    │ ORDER BY event_time │
                    │ LIMIT ? OFFSET ?    │
                    └───────────┬─────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  PostgreSQL GIN     │
                    │  Index Scan         │
                    │  (Fast!)            │
                    └───────────┬─────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  SearchResult       │
                    │  + timeline_sequence│
                    └─────────────────────┘
```

---

## File Dependency Map

```
app/
├── core/
│   ├── module_contracts.py ◄─────────────────┐
│   ├── vault_paths.py ◄───────────────────┐  │
│   └── utc.py ◄────────────────────────────┼──┼──┐
│                                           │  │  │
├── models/                                 │  │  │
│   └── models.py ◄─────────────────────────┼──┼──┼──┐
│       • VaultItem                         │  │  │  │
│       • Incident                        │  │  │  │
│       • VaultAuditLog                   │  │  │  │
│           ▲                             │  │  │  │
│           │                             │  │  │  │
├── services/                             │  │  │  │
│   ├── vault_ingestion.py ◄──────────────┼──┼──┼──┤
│   │   • VaultIngestionService             │  │  │  │
│   │   • IngestionRequest/Result           │  │  │  │
│   │   • register_function_group() ────────┘  │  │  │
│   │                                          │  │  │
│   ├── vault_search.py ◄─────────────────────┼──┤  │
│   │   • VaultSearchService                  │  │  │
│   │   • SearchCriteria/Result               │  │  │
│   │   • TimelineMode                        │  │  │
│   │   • register_function_group() ──────────┘  │  │
│   │                                           │  │  │
│   └── timeline_chronology.py (existing) ◄────┤  │
│       • Uses cloud events.json               │  │
│       • Separate from vault timeline         │  │
│                                              │  │
├── routers/                                   │  │
│   └── vault_all_in_one.py ◄───────────────────┼──┤
│       • All 15+ endpoints                   │  │
│       • Uses vault_ingestion.py ────────────┘  │
│       • Uses vault_search.py ─────────────────┘  │
│                                                  │
└── main.py ◄──────────────────────────────────────┘
    • Imports vault_all_in_one_router
    • Registers with FastAPI
    • Logs: "🏛️ ALL-IN-ONE Vault router connected"

alembic/
└── versions/
    └── a1b2c3d4e5f6_add_all_in_one_vault_tables.py
        • Creates vault_items
        • Creates incidents
        • Creates vault_audit_logs
        • Creates GIN indexes
```

---

## Module Contract Integration

```python
# How the vault registers with Semptify's contract system

┌─────────────────────────────────────────────────────────┐
│           app/core/module_contracts.py                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ModuleContractRegistry ─────┐                          │
│    • _contracts: dict        │                          │
│    • register()              │                          │
│    • validate()              │                          │
│                              │                          │
│         ▲                    │                          │
│         │                    │                          │
│    ┌────┴────────────────────┴──────────────┐          │
│    │                                          │          │
│    │   app/services/vault_ingestion.py        │          │
│    │   ─────────────────────────────────       │          │
│    │                                            │          │
│    │   register_function_group(                 │          │
│    │       FunctionGroupContract(               │          │
│    │           module="vault",                   │          │
│    │           group_name="vault_ingestion",    │          │
│    │           title="Vault Ingestion Service", │          │
│    │           inputs=("user_id", ...),         │          │
│    │           outputs=("item_id", ...),        │          │
│    │           deterministic=True, ◄────────────┼────┐   │
│    │       )                                     │    │   │
│    │   )                                         │    │   │
│    │                                             │    │   │
│    └─────────────────────────────────────────────┘    │   │
│                                                       │   │
│    ┌─────────────────────────────────────────────┐    │   │
│    │   app/services/vault_search.py              │    │   │
│    │   ───────────────────────────────────────  │    │   │
│    │                                             │    │   │
│    │   register_function_group(                 │    │   │
│    │       FunctionGroupContract(               │    │   │
│    │           module="vault",                   │    │   │
│    │           group_name="vault_search",        │    │   │
│    │           deterministic=True, ◄────────────┼────┼───┘
│    │       )                                     │    │
│    │   )                                         │    │
│    │                                             │    │
│    └─────────────────────────────────────────────┘    │
│                                                       │
└───────────────────────────────────────────────────────┘

# Deterministic = Same inputs always produce same outputs
# Critical for legal/evidence systems
```

---

## Route to Service Mapping

| Route | Handler | Service | Database |
|-------|---------|---------|----------|
| `POST /vault/items` | `ingest_vault_item()` | `VaultIngestionService.ingest()` | INSERT vault_items, vault_audit_logs |
| `GET /vault/items` | `search_vault_items()` | `VaultSearchService.search()` | SELECT with GIN indexes |
| `GET /vault/items/{id}` | `get_vault_item()` | Direct SQLAlchemy query | SELECT by PK |
| `PUT /vault/items/{id}` | `update_vault_item()` | `VaultIngestionService.update_item()` | UPDATE with audit log |
| `DELETE /vault/items/{id}` | `delete_vault_item()` | `VaultIngestionService.delete_item()` | DELETE with audit log |
| `GET /vault/timeline` | `get_vault_timeline()` | `VaultSearchService.search()` | ORDER BY timeline_mode |
| `GET /vault/incidents/{id}/timeline` | `get_incident_timeline()` | `VaultSearchService.get_timeline_by_incident()` | FILTER + ORDER BY |
| `POST /vault/incidents` | `create_incident()` | Direct SQLAlchemy | INSERT incidents |
| `GET /vault/search/metadata` | `search_by_metadata()` | `VaultSearchService.deep_metadata_search()` | JSONB containment |
| `GET /vault/search/location` | `search_by_location()` | `VaultSearchService.location_search()` | JSONB + distance calc |

---

## SSOT Compliance Check

```
┌─────────────────────────────────────────────────────────┐
│         SINGLE SOURCE OF TRUTH CHECKLIST                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ ✅ Vault Paths                                          │
│    Uses app/core/vault_paths.py constants               │
│    VAULT_DOCUMENTS, VAULT_TIMELINE, etc.               │
│                                                         │
│ ✅ Module Contracts                                     │
│    Registers via register_function_group()              │
│    FunctionGroupContract with deterministic=True        │
│                                                         │
│ ✅ Routing (via main.py)                                │
│    Uses route_user() for redirects                    │
│    Single auth function: get_current_user_id()        │
│                                                         │
│ ✅ Database Layer                                        │
│    Uses app/core/database.py Base, get_db()            │
│    UTC timestamps via app/core/utc.utc_now()          │
│                                                         │
│ ✅ Deterministic Behavior                               │
│    No AI in routing/sorting                           │
│    Same query = same results every time                │
│    Immutable timestamps                                │
│                                                         │
│ ✅ Stateless Design                                     │
│    Services are stateless                             │
│    All data in PostgreSQL                               │
│    No in-memory caching of results                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Reference: Adding to Existing Features

### Link Document Upload to Vault

```python
# In your existing document upload handler:

from app.services.vault_ingestion import ingest_vault_item

async def handle_upload(file, user_id):
    # 1. Save to cloud (existing code)
    cloud_path = await save_to_cloud(file)
    
    # 2. Extract metadata (existing code)
    extracted = await extract_metadata(file)
    
    # 3. NEW: Ingest to ALL-IN-ONE vault
    result = await ingest_vault_item(
        db=db,
        user_id=user_id,
        item_type="document",
        event_time=extracted.get("document_date"),
        record_time=datetime.now(timezone.utc),
        metadata={
            "filename": file.filename,
            "cloud_path": cloud_path,
            "extraction": extracted,
            "sha256": file_hash,
        },
        file_path=cloud_path,
        title=extracted.get("title"),
    )
    
    return {"cloud_path": cloud_path, "vault_item_id": result.item_id}
```

### Query Vault from Timeline

```python
## Integration with Existing Systems

### Timeline Chronology

The existing `app/services/timeline_chronology.py` works with cloud-based timeline (`Semptify5.0/Vault/timeline/events.json`). The ALL-IN-ONE metadata layer provides fast PostgreSQL queries as an index on top.

### Overlay System

Document overlays are stored in the vault at `Semptify5.0/Vault/.overlay/`. The ALL-IN-ONE layer indexes overlay metadata for fast searching while the actual overlay files stay in cloud storage.

### Query Vault from Timeline

```python
# In your existing timeline endpoint:

from app.services.vault_search import search_vault

async def get_timeline(user_id):
    # 1. Get cloud timeline (existing)
    cloud_events = await load_cloud_timeline(user_id)
    
    # 2. NEW: Query vault for enriched data
    vault_results = await search_vault(
        db=db,
        user_id=user_id,
        timeline_mode="event_time",
        limit=1000,
    )
    
    # 3. Merge or choose primary source
    # Cloud = portable, user-controlled
    # Vault = fast queries, audit trail
    return {
        "cloud_events": cloud_events,
        "vault_items": vault_results.items,
        "primary_source": "cloud",  # Or "vault" based on use case
    }
```

---

*This code map shows how the ALL-IN-ONE vault integrates with Semptify's existing SSOT architecture while maintaining clear separation between cloud (portable) and database (queryable) storage.*
