# Unified Overlay System - Design Document

**Status**: PARKED (Design Complete, Implementation Deferred)  
**Created**: 2026-04-20  
**Priority**: Post-Core-Mechanics  
**Blocked By**: Core mechanics stabilization, single source of truth implementation  

---

## Why This Is Parked

The overlay system requires a **unified implementation** to avoid the current situation of 3 separate overlay systems that don't align. Implementing it now would:
- Create technical debt before core mechanics are stable
- Risk conflicts with the ongoing "single source of truth" refactoring
- Duplicate effort if core patterns change

**Resume when**: Core mechanics (routing, workflow engine, cloud storage patterns) are stable and stateless.

---

## The Problem: Current State

Three separate overlay systems exist that don't align:

| System | Location | Storage | Gap |
|--------|----------|---------|-----|
| `OverlayManager` | `app/services/document_overlay.py` | Cloud: `Semptify5.0/Vault/.overlay/` | Separate from annotations |
| `DocumentOverlayService` | `app/services/document_overlay_service.py` | **Local: `logs/document_overlays/records.json`** | Breaks statelessness |
| Annotation Overlays | `app/routers/overlays.py` | Cloud: `.semptify/vault/overlays/` | Separate from processing |

**Missing**: Form-fill overlays, query/output system, redaction overlays

---

## The Solution: Unified Overlay Engine

### 1. Seven Core Needs

| Need | Description | Current State |
|------|-------------|---------------|
| **1. Vault Immutability Protection** | Original documents in `Vault/documents/` never modified; all mutations in overlay layers | Partial (two locations) |
| **2. Upload Traceability** | Every upload creates `vault_upload_manifest` overlay | Partial (local storage) |
| **3. Processing Result Storage** | AI processing stores results in overlays, not originals | Partial |
| **4. Annotation Layer** | Highlights, notes, footnotes, tracked edits | Separate system |
| **5. Overlay/Query Output** | Court packets as query layers, watermarked views, no server storage | Not implemented |
| **6. Identity Resolution** | `overlay_record_ids[]` links mutable records to vault artifacts | Not implemented |
| **7. Form-Fill Overlays** | Jurisdiction-specific forms as overlays on user's system | Not implemented |
| **8. PII Redaction** | Redaction as overlay layer, original untouched | Not implemented |

### 2. Canonical Storage Paths

Extend `app/core/vault_paths.py`:

```python
VAULT_OVERLAYS           = f"{VAULT_ROOT}/overlays"           # All overlay types
VAULT_OVERLAY_REGISTRY   = f"{VAULT_OVERLAYS}/registry.json"   # Master index
VAULT_OVERLAY_DOCUMENTS  = f"{VAULT_OVERLAYS}/documents"       # Per-document overlays
VAULT_OVERLAY_QUERIES    = f"{VAULT_OVERLAYS}/queries"         # Query/output overlays
VAULT_OVERLAY_FORMS      = f"{VAULT_OVERLAYS}/forms"           # Form-fill overlays
VAULT_OVERLAY_REDACTIONS = f"{VAULT_OVERLAYS}/redactions"      # Redaction overlays
```

### 3. OverlayType Enum

```python
class OverlayType(str, Enum):
    # 1. Upload Traceability
    VAULT_UPLOAD_MANIFEST = "vault_upload_manifest"
    
    # 2. Processing Results
    DOCUMENT_EXTRACTION = "document_extraction"
    DOCUMENT_CLASSIFICATION = "document_classification"
    TIMELINE_EXTRACTION = "timeline_extraction"
    PARTY_EXTRACTION = "party_extraction"
    
    # 3. Annotations
    HIGHLIGHT = "highlight"
    NOTE = "note"
    FOOTNOTE = "footnote"
    TRACKED_EDIT = "tracked_edit"
    
    # 4. Form-Fill
    FORM_FILL = "form_fill"
    FORM_SIGNATURE = "form_signature"
    
    # 5. Output/Query
    COURT_PACKET_QUERY = "court_packet_query"
    EVIDENCE_BUNDLE_QUERY = "evidence_bundle_query"
    WATERMARKED_VIEW = "watermarked_view"
    
    # 6. Redaction
    PII_REDACTION = "pii_redaction"
    SENSITIVE_REDACTION = "sensitive_redaction"
    
    # 7. Identity/Adapter
    IDENTITY_ADAPTER = "identity_adapter"
```

### 4. Unified Data Model

```python
class UnifiedOverlay(BaseModel):
    overlay_id: str              # ovl_{uuid}
    overlay_type: OverlayType
    document_id: str           # References vault document
    vault_path: str              # Original document cloud path
    
    # Ownership & provenance
    created_by: str              # User ID who created overlay
    created_at: datetime
    updated_at: datetime
    
    # Content (type-specific payload)
    payload: dict                # Type-specific data
    
    # Security chain
    prev_overlay_hash: Optional[str]  # Chain for audit
    overlay_hash: str            # Hash of this overlay's content
    
    # Metadata
    metadata: dict               # Source, reason, jurisdiction, etc.
    
    # For query overlays: ephemeral flag
    ephemeral: bool = False      # True for watermarked views (not persisted)
```

### 5. UnifiedOverlayManager (Cloud-Only, Stateless)

```python
class UnifiedOverlayManager:
    """
    Single source of truth for all overlay operations.
    Stateless: all storage is in user's cloud, no local files.
    """
    
    def __init__(self, storage_provider, user_id: str):
        self.storage = storage_provider
        self.user_id = user_id
    
    async def create_overlay(...)
    async def get_overlays(...)
    async def get_document_with_overlays(...)
```

### 6. OverlayQueryEngine

For court packets and watermarked output - no physical file copies, only query layers.

### 7. FormFillOverlay System

Jurisdiction-specific forms as overlays; user fills on their own system; Semptify stateless.

### 8. RedactionOverlay System

PII redaction as overlay layer; original untouched.

---

## Architectural Alternatives Considered

See detailed comparison in research notes. Summary:

| Approach | Verdict |
|----------|---------|
| **Layered Overlays** (chosen) | Best for legal integrity + statelessness |
| PDF Incremental Updates | PDF-only, hard to separate layers |
| Event Sourcing | Complex, overkill for current needs |
| Content-Addressed Storage | Good for deduplication, adds complexity |
| CRDTs | Overkill for single-user scenarios |
| Database-Centric | Violates user-controlled storage principle |
| Git-Like Repo | Doesn't handle binary files well |

---

## Implementation Plan (When Unparked)

### Phase 1: Core Types and Models
- `app/core/overlay_types.py` - OverlayType enum
- `app/models/unified_overlay_models.py` - Pydantic models

### Phase 2: Unified Manager
- `app/services/unified_overlay_manager.py` - Cloud-only overlay operations

### Phase 3: Specialized Engines
- `app/services/overlay_query_engine.py` - Court packets, watermarked output
- `app/services/form_fill_overlay.py` - Form-fill system
- `app/services/redaction_overlay.py` - PII redaction

### Phase 4: API and Migration
- `app/routers/unified_overlays.py` - API endpoints
- Migration path from legacy overlay systems

---

## Dependencies Before Resuming

- [ ] Core mechanics stable (routing, workflow engine)
- [ ] Single source of truth for vault paths implemented
- [ ] Stateless cloud storage patterns finalized
- [ ] User-controlled storage principle enforced everywhere

---

## Related Documents

- `app/core/vault_paths.py` - Canonical vault paths
- `docs/BUILD_OUT_STATUS.md` - Build status tracking
- `BLUEPRINT.md` - System architecture overview

---

## Notes

- Keep this document updated if core patterns change
- Review alternative architectures annually
- Consider event-sourced overlays if audit requirements grow
