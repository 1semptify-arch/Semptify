# Semptify Active Context

**Last Updated**: 2026-04-21

---

## 🎯 Current Priority: Select Next Major System

### ✅ COMPLETED: Unified Overlay System (2026-04-21)

| Component | File | Status |
|-----------|------|--------|
| **Core Types** | `app/core/overlay_types.py` | ✅ Complete |
| **Data Models** | `app/models/unified_overlay_models.py` | ✅ Complete |
| **Cloud Manager** | `app/services/unified_overlay_manager.py` | ✅ Complete |
| **API Router** | `app/routers/unified_overlays.py` | ✅ Complete |
| **Vault Integration** | `app/services/vault_upload_service.py` | ✅ Complete |
| **Router Integration** | `app/main.py` | ✅ Complete |
| **Old System Deprecated** | `document_overlay.py`, `document_overlay_service.py` | ✅ Marked |

**API Available**: `/api/unified-overlays/*`
**Storage**: `Semptify5.0/Vault/overlays/` (cloud-only, stateless)

### ✅ COMPLETED: Core Mechanics (2026-04-20)

| Area | Task | Status | Notes |
|------|------|--------|-------|
| **Routing** | Single source of truth for OAuth routing | ✅ Complete | `route_user()` in `workflow_engine.py` |
| **Workflow** | Stateless behavior, deterministic routing | ✅ Complete | Removing stateful fallbacks |
| **Vault** | Cloud storage patterns finalized | ✅ Complete | Path constants in `vault_paths.py` |

### 🅿️ PARKED (Awaiting Decision)

| Project | Design Doc | Status | Blocked By |
|---------|------------|--------|------------|
| **rehome.html / Identity Recovery** | Research encrypted alternative | 🅿️ PARKED | User researching encrypted format vs plain HTML |

### ✅ COMPLETED: Document Delivery System

| Component | File | Status |
|-----------|------|--------|
| **Page Contracts** | `app/core/page_contracts.py` | ✅ Complete (inbox, send, signature flows) |
| **Data Models** | `app/models/document_delivery_models.py` | ✅ Complete |
| **Service Layer** | `app/services/document_delivery_service.py` | ✅ Complete |
| **API Router** | `app/routers/document_delivery.py` | ✅ Complete |
| **Send HTML** | `static/delivery_send.html` | ✅ Complete (w/ communication integration) |
| **Inbox HTML** | `static/delivery_inbox.html` | ✅ Complete |
| **Signer HTML** | `static/document_signer.html` | ✅ Complete (fill, sign, chat, reject) |
| **Main Integration** | `app/main.py` | ✅ Complete |

**API Available**: `/api/delivery/*`
**Delivery Types**: REVIEW_REQUIRED, SIGNATURE_REQUIRED, PROCESS_SERVER (future)
**Who Can Send**: Advocate, Manager, Legal, Admin
**Storage**: Cloud overlays in recipient vault

### ✅ COMPLETED: Communication System (2026-04-21)

| Component | File | Status |
|-----------|------|--------|
| **Data Models** | `app/models/communication_models.py` | ✅ Complete |
| **Service Layer** | `app/services/communication_service.py` | ✅ Complete |
| **API Router** | `app/routers/communication.py` | ✅ Complete |
| **Browser UI** | `static/document_signer.html` | ✅ Complete |
| **Overlay Type** | `app/core/overlay_types.py` | ✅ Added COMMUNICATION |
| **Main Integration** | `app/main.py` | ✅ Complete |

**API Available**: `/api/communications/*`
**Features**:
- Direct messaging between tenant and all roles
- Document collaboration threads
- In-browser document filling and signing
- Signed documents saved to user's vault
- Real-time chat interface

**Storage**: Cloud overlays (COMMUNICATION type) in `Semptify5.0/Vault/communications/`

### 🔍 READY TO START (Pick One)

| Option | What | Why Now |
|--------|------|---------|
| **1** | Identity Recovery (rehome.html replacement) | Encrypted identity anchor file format research |
| **2** | Form-Fill Overlays | Wire up jurisdiction-specific form overlays in unified system |
| **3** | Redaction System | PII redaction overlay implementation |
| **4** | Timeline Enhancement | Advanced timeline visualization and chronology |
| **5** | Court Forms Integration | Connect form-fill overlays to court filing system |

---

## ✅ UNPARKED (Recently Completed)

| Project | Design Doc | Status |
|---------|------------|--------|
| **Unified Overlay System** | `docs/OVERLAY_SYSTEM_DESIGN.md` | ✅ Complete and deployed |

---

## 🚫 Anti-Priorities (Don't Start These)

Things that might seem important but should NOT be worked on now:

1. **New features** that aren't core mechanics
2. **Refactoring** unrelated to statelessness
3. **Documentation** that isn't critical path
4. **Testing** of non-core systems

---

## ✅ Definition of "Core Mechanics Stable"

- [ ] `route_user()` is single source of truth for all routing
- [ ] No hardcoded redirect tables anywhere
- [ ] No local file storage for user data (all cloud)
- [ ] Deterministic behavior: same input = same output
- [ ] Stateless: no server-side session state

---

## 📋 Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-04-21 | ✅ Document Send uses Communication System | Send creates conversation thread + delivery record |
| 2026-04-21 | ✅ Document Rejection saves to vault | Rejection records stored as COMMUNICATION overlays with watermark |
| 2026-04-21 | ✅ Completed Communication System | Document fill/sign + messaging + vault storage |
| 2026-04-21 | ✅ Completed Unified Overlay System | All components integrated, vault upload migrated |
| 2026-04-21 | Ready for next major system | Core mechanics + overlays stable |
| 2026-04-20 | Parked Unified Overlay System | Core mechanics must stabilize first |
| 2026-04-20 | Prioritized stateless routing | Foundation for all other work |

---

## 🔗 Quick Links

- **Parked Design**: `docs/OVERLAY_SYSTEM_DESIGN.md`
- **Build Status**: `docs/BUILD_OUT_STATUS.md`
- **Blueprint**: `BLUEPRINT.md`
- **Vault Paths**: `app/core/vault_paths.py`

---

*This file is the single source of truth for what is being worked on RIGHT NOW.*
