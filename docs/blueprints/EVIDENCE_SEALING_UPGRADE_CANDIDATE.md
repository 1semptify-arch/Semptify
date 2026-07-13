# Evidence Sealing & Chain-of-Custody — Future Upgrade Candidate
**Status:** SHELVED — for consideration after the current finish-and-harden pass is solid
**Source:** Adapted from an external "Semptify Master Blueprint Pack" (generic, not codebase-aware)
**Verdict on the source doc:** Mostly not usable as-is. It duplicates `page_composer` / `context_engine`, invents a second set of pillar names, and its API spec would violate the `product_manifest.py` registration rule if built literally. The one piece worth keeping is below, rewritten to actually fit.

---

## 1. What's worth keeping (and why)

The original doc's "Semantic Classifier → Highlight Engine → PDF Evidence Assembler" pipeline is mostly redundant — you already have that composition job done by `page_composer` + `context_engine`. But it has one real gap-filler:

**Sealed, hash-verified, chain-of-custody PDF export.**

That's a genuine capability gap. It fits squarely under **Govern** — your silent audit/defensibility layer — not as a new pillar, not as a new layout system, just as one module that makes any existing document or generated form legally defensible on export.

Everything else from the original doc (Semantic Classifier, Block Composer, Highlight Engine, Knowledge Stream/Ledger/Narrative layout branches, the Jinja2/Liquid template pack, the `/classify` `/compose-blocks` `/highlight` API surface) is **dropped**. You already have working equivalents or don't need them.

---

## 2. What it would actually be, in Semptify terms

**Module name:** `evidence_seal` (folder: `app/modules/evidence_seal/`)
**Pillar:** Govern
**Tier:** `ADMIN` (or `EXTENDED` if it should ship alongside eviction-defense forms specifically — decide at build time, not now)

### Job
Take a document that already exists somewhere in Semptify (a vault file, a composed page, a generated court form) and produce a sealed PDF with:
- SHA-256 integrity hash
- Timestamp + chain-of-custody log entry (who/what/when triggered the seal)
- An annotation/highlight layer *if* the source content already carries highlight metadata — it does NOT do its own semantic classification, it just renders whatever classification already exists upstream

### What it does NOT do
- No new semantic classifier — `context_engine` already extracts and tags facts
- No new "Block Composer" — `page_composer` already assembles sections from multiple sources
- No new template language — you already use Jinja2 at `app/templates/`
- No new layout routes (`/knowledge-stream`, `/ledger`, `/narrative`) — those aren't pillars, they're presentation modes, and you don't need three parallel ones

### Folder structure (matches your standard)
```
app/modules/evidence_seal/
├── __init__.py        # exports router + models
├── router.py           # FastAPI APIRouter, prefix="/api/evidence-seal"
├── service.py           # hashing + chain-of-custody + PDF sealing logic
├── models.py             # SQLAlchemy models, uses app.core.database.Base
├── config.py               # reads from .env via get_settings()
└── README.md                # what this module does
```

### Minimal router (matches your pattern exactly)
```python
from fastapi import APIRouter, Depends
from app.core.capabilities import require_capability

router = APIRouter(
    prefix="/api/evidence-seal",
    tags=["Evidence Seal"],
    dependencies=[Depends(require_capability("app.modules.evidence_seal.router"))],
)

@router.get("/health")
async def health():
    return {"status": "healthy", "module": "evidence_seal"}

@router.post("/seal")
async def seal_document(document_id: str):
    """Seal an existing vault document into a hash-verified, chain-of-custody PDF."""
    ...
```

### Registration (product_manifest.py — three-step rule, nothing more)
```python
_register(
    "app.modules.evidence_seal.router",
    tags=("Evidence Seal",),
    tier=ProductTier.ADMIN,
    optional=True,
    lifecycle="experimental",       # flip to "stable" once it's proven out
    requires_gate="vault_initialized",
    upl_risk_tier=UPLRiskTier.LOW,  # it seals documents, doesn't give legal advice
    log_message="Evidence Seal module loaded",
)
```
Plus the matching `CAPABILITY_DEFAULTS` entry and the `import app.modules.evidence_seal.models` line in `app/core/database.py`. No other file needs to change. `main.py` is never touched directly.

### Data source
Pulls the document from wherever it already lives — `vault_engine` for stored files, `page_composer.compose_page()` for a composed view, or a generated form — rather than re-implementing intake or extraction.

---

## 3. When to revisit this

Not now. Reasonable triggers to re-open this doc later:
- Stub count is near zero and the `/ship` backlog is clear
- The vault audit-log branch (flagged as your highest-risk unmerged item) is resolved, since chain-of-custody logging should sit on top of that, not duplicate it
- You have an actual court-facing need for a sealed export (vs. a nice-to-have)

## 4. What to tell an agent if this gets picked back up
"Build `evidence_seal` per `EVIDENCE_SEALING_UPGRADE_CANDIDATE.md`. Do not touch `main.py`. Do not build a new semantic classifier or template layer — pull content from `page_composer` and `context_engine`, and check the vault audit-log branch status before writing new chain-of-custody logic."
