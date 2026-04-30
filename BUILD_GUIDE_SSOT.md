# Semptify 5.0 Build Guide (SSOT)

**Purpose:** Single source of truth for build status, testing results, and known issues.  
**Last Updated:** April 29, 2026  
**Build Type:** Core (Tenant Role Only)  
**Status:** Reconnect Flow VERIFIED ✅

---

## ✅ Core Philosophy

> "Document Everything. Avoid the Pitfalls."

**Semptify 5.0 Core** = Lightweight tenant journal + document vault + rights education.  
No AI, no legal filing, no campaigns, no multi-user. Just quiet documentation.

---

## 🎯 Active Features (Core)

### 📚 Library (Rights & Education)
- [ ] `law_library.py` - State laws, statutes
- [ ] `state_laws.py` - State-specific tenant rights

### 🏢 Office (Document Management)
- [ ] `documents.py` - Upload, processing
- [ ] `vault.py` - Cloud storage vault
- [ ] `briefcase.py` - Document viewer
- [ ] `timeline_unified.py` - Timeline/journal viewer
- [ ] `pdf_tools.py` - PDF manipulation
- [ ] `preview.py` - Document preview
- [ ] `document_converter.py` - Format conversion

### 🔧 Tools (Analysis & Utilities)
- [ ] `legal_analysis.py` - Evidence classification, merit assessment
  - ✅ Direct document analysis (no dependencies)
  - ⏸️ Case-based analysis requires Extended (tenancy_hub)

### 🆘 Help (Onboarding)
- [ ] `onboarding.py` - Role selection, storage setup
- [ ] `role_ui.py` - UI routing
- [ ] `workflow.py` - Process orchestration

---

## 🧪 Testing Checklist

### Welcome Flow
| Step | URL | Status | Notes |
|------|-----|--------|-------|
| 1. Welcome Page | `/static/public/welcome.html` | ⏳ Testing | Check CTAs work |
| 2. New User Path | `/onboarding/select-role.html` | ⏳ Testing | Only Tenant selectable |
| 3. Returning User | `/storage/reconnect` | ✅ **VERIFIED** | Session valid → role home; Invalid → OAuth → role home |
| 3a. **Return to Task** | `/storage/reconnect?return_to=/timeline/view/123` | ✅ **VERIFIED** | Mid-task auth expiry → return to previous page after reauth |
| 4. Storage Select | `/onboarding/storage-select.html` | ⏳ Testing | Provider selection |
| 5. OAuth Flow | `/storage/connect` | ⏳ Testing | Google/Dropbox/OneDrive |
| 6. Tenant Home | `/tenant/home` | ⏳ Testing | Dashboard loads |

### Document Flow
| Step | Endpoint | Status | Notes |
|------|----------|--------|-------|
| Upload | `/api/documents/upload` | ⏳ Testing | To vault |
| View Timeline | `/api/timeline-unified` | ⏳ Testing | Journal view |
| View Briefcase | `/api/briefcase` | ⏳ Testing | Document viewer |
| Legal Analysis | `/api/legal-analysis/classify-evidence` | ⏳ Testing | Direct analysis |

---

## 🐛 Known Issues

### Critical (Block Release)
- [ ] None logged yet

### Major (Fix Before Release)
- [x] **Reconnect → Storage Selection Loop** — **FIXED & VERIFIED** ✅
  - **Root cause:** `return_to=/storage/reconnect` caused OAuth callback to loop back to reconnect page
  - **Fix 1 (storage.py:2369):** Removed `return_to` parameter from OAuth URL - now uses `route_user()` for landing
  - **Fix 2 (storage.py:780-785):** Added session validation to `/reconnect` endpoint before OAuth
  - **Final flow:**
    - Valid session → `route_user(uid)` → role home (NO OAuth)
    - Invalid session → silent OAuth → `route_user(uid)` → role home

### Minor (Defer)
- [x] **Browser Preview Cross-Origin Issue** — Preview proxy at `127.0.0.1:58057` cannot load app URLs at `localhost:8000` due to frame security restrictions. Affects:
  - `/storage/reconnect` → `localhost:8000/storage/reconnect`
  - `/onboarding/select-role.html` → `localhost:8000/onboarding/select-role.html`
  
  **Workaround:** Test directly at `http://localhost:8000` (not through preview proxy).

---

## 📦 Deferred to Extended

These features are **disabled** in Core build but code is preserved:

### AI/Brain Features
- `brain.py`, `copilot.py`, `emotion.py`, `auto_mode.py`
- Requires: User consent, heavy compute

### Legal/Court Features
- `court_forms.py`, `court_packet.py`, `eviction_defense.py`, `case_builder.py`
- Requires: Legal validation, jurisdiction data

### Analytics/Research
- `analytics.py`, `research.py`, `crawler.py`
- Requires: User opt-in, privacy review

### Multi-User/Collaboration
- `communication.py`, `document_delivery.py`, `invite_codes.py`
- Requires: Advocate/legal role enablement

---

## 📦 Other Division (Future Products)

These serve different purposes than Core tenant journaling:

| Feature | Division | Purpose |
|---------|----------|---------|
| `campaign.py` | Marketing/Public | Public awareness campaigns |
| `public_exposure.py` | Advocacy | Bad actor exposure |
| `fraud_exposure.py` | Investigation | Fraud pattern detection |

---

## 🔧 Modular Architecture

### How to Enable Extended Features

1. **Edit `app/main.py`**
2. **Find the Extended section** (commented out)
3. **Uncomment the router import:**
   ```python
   # Before (disabled)
   court_forms_router = None
   
   # After (enabled)
   court_forms_router = _safe_router_import("app.routers.court_forms")
   ```
4. **Restart app**

### Add-On Loading (Future)
```python
# Environment-based feature flags
SEMPFIFY_FEATURE_SET=core        # Only Core
SEMPFIFY_FEATURE_SET=extended    # Core + Extended
SEMPFIFY_FEATURE_SET=full        # Everything
```

---

## � Task Recovery (return_to)

When auth expires mid-task, user can return to their previous state after reauth.

### Usage
```
User at /timeline/view/123 → Auth expires
→ Redirect: /storage/reconnect?return_to=/timeline/view/123
→ OAuth flow
→ Callback returns to: /timeline/view/123 (not home)
```

### Implementation Details
- **Entry:** `storage.py:763` - `return_to` query param on `/reconnect`
- **Validation:** Only local paths allowed (`/...`, not `//...` or `https://`)
- **Session valid:** Returns directly to `return_to` URL (skips OAuth)
- **Session invalid:** Passes `return_to` through OAuth → callback restores it
- **HTML picker:** JavaScript threads `RETURN_TO` through OAuth state

### Security
- External URLs rejected (prevent open redirect)
- Double slashes rejected (`//evil.com`)
- Empty/null `return_to` falls back to `route_user()` → home

---

## Build Log

### April 29, 2026 - Modular Core Restructure
- Reorganized `main.py` into CORE / EXTENDED / OTHER DIVISION
- Made `legal_analysis.py` brain-optional (works standalone)
- Moved `briefcase.py`, `timeline_unified.py` to Core
- Preserved `campaign.py`, `public_exposure.py`, `fraud_exposure.py` in Other Division
- Fixed `app/services/` import structure
- Fixed reconnect loop (`storage.py:780-803`)
- Added `return_to` task recovery
- Created `GOVERNING_SYSTEM_SSOT.md` — conductor architecture documented
- Created `workflow_validator.py` — admin dashboard for conductor verification
- **VERIFIED:** Cookie auth, user ID parsing, routing system, workflow decisions all operational

---

## Debug Commands

```bash
# Start server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Check imports
python -c "from app.main import app; print('OK')"

# Check active routes
curl http://localhost:8000/api/health
```

---

## ✅ Release Criteria

- [ ] Welcome → Role Select → Storage → OAuth → Tenant Home flows work
- [ ] Document upload to vault works
- [ ] Timeline/Briefcase viewers work
- [ ] Legal analysis (direct) works
- [ ] No errors in logs
- [ ] All non-Core routers disabled

