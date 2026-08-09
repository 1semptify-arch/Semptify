# TODO: Next Session — Post-Ship Tasks

**Date:** 2026-06-08 (Evening Session Ship Complete)
**Commit:** Shipped identity statements + funding module

---

## Priority 1 — Test Funding Module

- [ ] Create database tables for funding module

  ```python
  from app.core.database import engine
  from app.modules.funding_mgmt.models import Base
  Base.metadata.create_all(bind=engine)
  ```

- [ ] Live test `/admin/funding/` dashboard GUI
- [ ] Verify `/admin/funding/prospectus` page loads correctly
- [ ] Test admin access control (non-admins should be blocked)

---

## Priority 2 — Grant Applications

- [ ] **LSC (Legal Services Corporation)** — Federal grant application
- [ ] **Ford Foundation** — Housing justice program proposal
- [ ] **Suffolk LIT Lab** — Partnership outreach for technical credibility
- [ ] **HOME Line** — Minnesota tenant advocacy partnership
- [ ] Populate funding module with real prospects using `/admin/funding/`

---

## Priority 3 — ID System License Headers

- [ ] Add demonstration prototype headers to `app/core/id_gen.py`
- [ ] Add demonstration prototype headers to `app/core/user_id.py`
- [ ] Add confidentiality notice to ID system files
- [ ] Document "Semptify Secured ID" as planned post-funding feature

---

## Priority 4 — From Previous Sessions (Document Upload)

- [ ] Live test document upload (from 2026-06-06 session pending)
- [ ] Verify documents appear in vault after upload
- [ ] Test document integrity verification flow

---

## Quick Commands for Next Session

```bash
## Activate environment
.\venv311\Scripts\Activate.ps1

## Start app
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

## Create funding tables
python -c "from app.core.database import engine; from app.modules.funding_mgmt.models import Base; Base.metadata.create_all(bind=engine)"
```

---

## Notes

- Funding module is admin-only (no SSOT constraints)
- All identity/ethics statements now in canonical docs
- App deployed to Render — verify live site after deploy completes
