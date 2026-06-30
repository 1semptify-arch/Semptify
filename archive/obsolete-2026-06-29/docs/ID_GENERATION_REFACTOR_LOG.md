# ID Generation Refactor — Change Log & SSOT Registry

**Date:** 2025-04-21  
**Scope:** All `uuid4()` calls eliminated from `app/` directory  
**New SSOT:** `app/core/id_gen.py`

---

## 1. Single Source of Truth (NEW)

### `app/core/id_gen.py`
- **Purpose:** Centralized ID generation for all entities
- **Format:** `{prefix}_{16-char alphanumeric}` (e.g., `doc_K8mXp2nR4jW7qF9a`)
- **Entropy:** ~95 bits (16 chars from 62-char alphabet)
- **Function:** `make_id(prefix: str, length: int = 16) -> str`
- **Security:** Uses `secrets.choice()` (cryptographically secure)

**SSOT Rule:** All entity IDs MUST be generated through this module. No inline UUID generation allowed.

---

## 2. Prefix Registry (Entity Types)

| Prefix | Entity | Files Using |
|--------|--------|-------------|
| `doc` | Document | documents.py, document_pipeline.py, document_intelligence.py |
| `evt` | Timeline Event | documents.py, briefcase.py, calendar.py, document_intelligence.py, document_flow_orchestrator.py |
| `cal` | Calendar Event | calendar.py |
| `con` | Contact | contacts.py, document_flow_orchestrator.py |
| `inv` | Invite | advocate_invite.py |
| `job` | Background Job | job_processor.py |
| `anl` | Analytics Event | analytics_engine.py |
| `aud` | Audit Entry | audit.py |
| `req` | Request/Correlation ID | logging_middleware.py, distributed_mesh.py, mesh_network.py |
| `msg` | Mesh Message | distributed_mesh.py, mesh_network.py |
| `sigreq` | Signature Request | communication_models.py |
| `sig` | Signature | communication_models.py |
| `att` | Attachment | communication_models.py |
| `del` | Delivery | document_delivery_models.py |
| `ext` | Extraction | batch_operations.py |
| `hlt` | Highlight | briefcase.py |
| `ann` | Annotation | briefcase.py |
| `ovl` | Overlay | overlays.py, unified_overlay_models.py |
| `plan` | Plan | module_hub.py |
| `camp` | Campaign | campaign.py |
| `wiz` | Wizard/Complaint | complaint_wizard.py |
| `conv` | Conversation | copilot.py |
| `frd` | Fraud Analysis | fraud_models.py |
| `prs` | Person/Party | batch_operations.py |
| `chk` | Checkpoint | research_module.py |
| `fx` | Function/Task | positronic_mesh.py |
| `not` | Notification | notification_service.py |
| `pack` | Info Pack | module_sdk.py |
| `batch` | Batch Operation | batch_operations.py |
| `item` | Batch Item | batch_operations.py |
| `collab` | Collaboration | mesh_network.py |
| `ask` | Ask/Request | mesh_network.py |
| `node` | Mesh Node | distributed_mesh.py |
| `upd` | Update | module_hub.py |
| `trn` | Training Example | document_training.py |
| `evid` | Evidence Item | tenant_defense.py |
| `act` | Action Item | document_intelligence.py |
| `cout` | Case Outcome | court_learning.py |
| `def` | Defense Outcome | court_learning.py |
| `mot` | Motion Outcome | court_learning.py |
| `cmp` | Complaint Draft | complaint_wizard.py |

---

## 3. Files Modified (34 Total)

### Models (2)
- `app/models/communication_models.py` — Replaced `uuid4` with `make_id()` for `sigreq`, `sig`, `att`
- `app/models/document_delivery_models.py` — Replaced `uuid4` with `make_id("del")`

### Routers (10)
- `app/routers/briefcase.py` — `doc`, `hlt`, `ann`, `evt` prefixes
- `app/routers/contacts.py` — `con` prefix for contacts/interactions
- `app/routers/overlays.py` — `ovl` prefix
- `app/routers/calendar.py` — `cal` prefix
- `app/routers/documents.py` — `evt` prefix (timeline events)
- `app/routers/cloud_sync.py` — Multiple prefixes for sync entities
- `app/routers/copilot.py` — `conv` prefix for conversations
- `app/routers/advocate_invite.py` — `inv` prefix
- `app/routers/funding_search.py` — Removed dead `import uuid`
- `app/routers/campaign.py` — `camp` prefix

### Core Modules (11)
- `app/core/distributed_mesh.py` — `node`, `req`, `msg`, `evt` prefixes
- `app/core/mesh_network.py` — `req`, `collab`, `ask` prefixes
- `app/core/batch_operations.py` — `batch`, `item`, `ext`, `prs` prefixes
- `app/core/module_hub.py` — `pack`, `req`, `upd` prefixes
- `app/core/job_processor.py` — `job` prefix
- `app/core/positronic_mesh.py` — `fx` prefix
- `app/core/websocket_manager.py` — `sess`, `ws` prefixes
- `app/core/analytics_engine.py` — `anl` prefix
- `app/core/audit.py` — `aud` prefix
- `app/core/logging_middleware.py` — `req` prefix (request IDs)
- `app/core/id_gen.py` — **NEW SSOT FILE**

### Services (7)
- `app/services/document_intelligence.py` — `doc`, `evt`, `act` prefixes
- `app/services/document_flow_orchestrator.py` — `con`, `evt` prefixes
- `app/services/eviction/court_learning.py` — `cout`, `def`, `mot` prefixes
- `app/services/complaint_wizard.py` — `cmp` prefix
- `app/services/document_pipeline.py` — `doc` prefix
- `app/services/document_training.py` — `trn` prefix
- `app/services/document_registry.py` — Replaced `uuid4().hex[:4]` with `secrets.token_hex(2)` for random suffix (format preserved)

### Modules (2)
- `app/modules/tenant_defense.py` — `evid` prefix
- `app/modules/research_module.py` — `chk` prefix

### SDK (1)
- `app/sdk/module_sdk.py` — `pack` prefix

### Application (1)
- `app/main.py` — `req` prefix for request ID middleware

---

## 4. Exception: Preserved Formats

### Document Registry (`app/services/document_registry.py`)
- **Format:** `SEM-{YYYY}-{NNNNNN}-{XXXX}` (e.g., `SEM-2025-000042-A7B3`)
- **Status:** Unchanged (deterministic sequential format preserved)
- **Change:** Only replaced `uuid4().hex[:4]` with `secrets.token_hex(2).upper()` for the 4-char random suffix
- **Reason:** This format is auditable and must remain consistent for legal document tracking

---

## 5. Verification

```bash
# Confirm zero uuid4() calls remain
grep -r "uuid4()" app/ --include="*.py"
# Result: No matches

# Confirm no dead imports
grep -r "^import uuid$" app/ --include="*.py"
grep -r "^from uuid import" app/ --include="*.py"
# Result: No matches
```

---

## 6. Foreign Key Column Sizes (Post-Refactor)

All FK columns now match the new ID format sizes:

| Table | Column | Size | References |
|-------|--------|------|------------|
| `timeline_events` | `id` | String(36) | PK |
| `timeline_events` | `user_id` | String(24) | users.id |
| `timeline_events` | `parent_event_id` | String(36) | self |
| `documents` | `id` | String(36) | PK |
| `documents` | `user_id` | String(24) | users.id |
| `documents` | `attorney_id` | String(36) | nullable |
| `calendar_events` | `id` | String(36) | PK |
| `calendar_events` | `user_id` | String(24) | users.id |
| `complaints` | `id` | String(36) | PK |
| `complaints` | `user_id` | String(24) | users.id |
| `vault_items` | `item_id` | Integer | PK (autoincrement) |
| `vault_items` | `user_id` | String(24) | users.id |

---

## 7. Migration Notes

- No database migration required for ID format (same String(36) size)
- Existing UUID-based IDs remain valid (backward compatible)
- New IDs generated going forward use the `{prefix}_{16char}` format
- Mixed ID formats in same table are acceptable (old UUIDs, new prefixed IDs)

---

## 8. SSOT Compliance

| Rule | Status |
|------|--------|
| All IDs generated through `app/core/id_gen.py` | ✅ |
| No inline `uuid4()` calls | ✅ |
| No `import uuid` in app/ | ✅ |
| Prefix indicates entity type | ✅ |
| Document registry format preserved | ✅ |
