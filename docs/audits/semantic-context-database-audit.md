# Audit: Semantic Context Database System for Semptify

**Date:** 2026-08-19
**Author:** Devin (per request of Project Owner)
**Purpose:** Provide a complete, objective, self-contained audit of the semantic context storage/retrieval problem in Semptify, so an independent team with no prior exposure can evaluate the full problem space and propose solutions — including ones not considered by the current team.
**Status:** Read-only audit. No code was changed. No solution is prescribed.

---

## 1. Executive Summary

Semptify has a half-built semantic context retrieval system. The retrieval **interface** is designed, built, and tested. The **semantic engine** behind it was never implemented. The reason is not neglect — it is a deliberate deferral caused by a naming collision, an unproven privacy model, and a conflation of two separable problems into one ADR.

There are three distinct things called "semantic" in this codebase. Only one of them (the rule-based date classifier) is built and working. The other two — an embedding pipeline for tenant documents, and a semantic retrieval layer for curated content — are unbuilt, and they are blocked for different reasons. This audit separates them so an independent team can evaluate each on its own merits.

---

## 2. What Semptify Is (for outsiders)

Semptify is a no-cost, open-source, 501(c)(3) public utility for renters. It helps tenants document housing problems, understand their rights, and organize records into a case file they can hand to an advocate or attorney.

**Four pillars:**
- **RECORD** — capture/organize evidence (vault, timeline, documents, journal)
- **KNOW** — legal literacy (law library, state laws, context engine)
- **ACT** — take action (complaint wizard, court prep, eviction defense)
- **GOVERN** — platform operations (admin, analytics, security)

**Architecture trust model:** A tenant's cloud storage (Google Drive, Dropbox, OneDrive) IS their identity. No passwords, no usernames, no email capture. Documents stay in the tenant's own account. Semptify servers never hold tenant document content.

**Tech stack:** FastAPI (Python 3.11.9 — hard mandate, non-negotiable), async SQLAlchemy, SQLite (dev) / PostgreSQL via asyncpg (prod on Render), Jinja2 templates, WebSocket events.

**Scale:** ~123 modules, ~1,050 API endpoints, 80 HTML templates. Maintained primarily by one person with AI tools. Donation-funded.

**North star metric:** Time to Real Help — the faster a tenant gets from crisis to a real next step, deadline, or human resource, the better Semptify is doing.

---

## 3. The Problem Statement

Semptify needs a system that can answer this question at render time:

> *"Given what this tenant is looking at right now (a button, a field, a page), what should we explain to them, and how much?"*

This is the **Information Orchestrator** (ADR-0008). It works by:
1. Attaching structured metadata (an "Object Envelope") to every explainable UI object.
2. Retrieving the best-matching human-written explanation from a curated store.
3. Tailoring the explanation depth to how familiar the tenant is with this kind of object.

Step 2 is where the gap is. The retrieval is currently **metadata-only matching** (tag overlap, jurisdiction, pillar, review status). It was designed as a placeholder for **semantic retrieval** (embedding similarity), but the embedding engine was never built. The question this audit poses:

> **What is the right semantic context database system for Semptify, given its constraints?**

---

## 4. The Three "Semantic" Systems (naming collision — read this first)

The word "semantic" appears in three unrelated places in the codebase. This is the primary source of confusion for anyone approaching this problem.

### 4.1 Semantic Context Engine (rule-based, BUILT, WORKING)

- **File:** `app/services/semantic_context_engine.py`
- **What it does:** Takes raw OCR text from a scanned document and classifies date mentions by semantic role (signed, issued, effective, deadline, etc.) using regex rules and trigger phrases.
- **How it works:** Pure rule-based/regex. No embeddings, no vector similarity, no LLM (an LLM fallback is reserved but not required).
- **Status:** Built, tested, in production. Resolved as todo-036 (2026-07-28).
- **Relevance to this audit:** None, beyond the name collision. This system has nothing to do with embedding-based semantic retrieval or vector databases.

### 4.2 ADR-0007 Embedding Pipeline (client-side, NEVER BUILT)

- **ADR:** `docs/adr/0007-ocr-semantic-reasoning-privacy.md`
- **What it was designed to do:** Generate embeddings of **tenant documents** (leases, notices, receipts) for document-type classification and matching against a "Question Atlas."
- **How it was designed to work:** Client-side embedding generation using all-MiniLM-L6-v2 run via WASM/ONNX in the tenant's browser. Only the resulting embedding vector (a number list, not readable text) would cross to Semptify's servers. Raw document text never leaves the device.
- **Status:** BETA — not Accepted. Never implemented. No `sentence-transformers`, `transformers`, or embedding module exists anywhere in the codebase (confirmed via todo-068 preflight).
- **Why it wasn't built:** The privacy model is unproven. Four success criteria for promotion to Accepted are all unchecked (see §7 below).

### 4.3 ADR-0008 Layer 2 Retrieval (metadata placeholder, BUILT, DESIGNED FOR SWAP)

- **ADR:** `docs/adr/0008-information-orchestrator.md` §2.2
- **File:** `app/modules/context_engine/retrieval.py`
- **What it does:** Ranks curated explanation entries against an Object Envelope to find the best explanation to show the tenant.
- **How it works today:** Metadata-only scoring — weighted match on subject_tags overlap (0.4), jurisdiction (0.2), pillar (0.2), review_status (0.2). A confidence threshold (`LAYER2_CONFIDENCE_THRESHOLD = 0.75`) acts as a score floor.
- **How it was designed to work eventually:** The same interface would accept real cosine similarity scores from an embedding model, replacing the metadata scorer without touching callers.
- **Status:** Built and tested as a placeholder. The embedding engine it was designed to swap in is the unbuilt ADR-0007 pipeline.
- **Relevance to this audit:** This is the primary consumer of whatever semantic database system is chosen.

### The conflation

ADR-0008 §2.2 originally said Layer 2 would "retrieve best-matching Layer 1 entries via embedding similarity (all-MiniLM-L6-v2, offline), reusing an existing OCR semantic pipeline." But that pipeline (ADR-0007) did not exist. When the ADR-0008 authors discovered this, they revised Layer 2 to metadata-only matching and deferred the embedding pipeline as todo-077, "decoupled from the pilot's critical path."

The deferral was correct for shipping the pilot. But it bundled two different embedding needs into one deferred task:
- **Embedding curated content** (Layer 1 explanation entries, ContextFacts) — Semptify's own human-authored content, no tenant PII, no privacy constraint.
- **Embedding tenant documents** (leases, notices) — tenant PII, hard privacy constraint requiring client-side processing.

These are different problems with different constraints. They were never separated.

---

## 5. Current Architecture — What Exists Today

### 5.1 The Information Orchestrator (ADR-0008)

Seven components. Two are foundational schemas; the rest read from them.

#### Object Envelope (`app/core/context_envelope.py`)
Per-object metadata declared alongside every explainable UI element:

| Field | Type | Purpose |
|---|---|---|
| `object_id` | string | Unique identifier for this object type |
| `object_type` | enum | `field` \| `block` \| `button` \| `module_output` \| `page_zone` |
| `pillar` | enum | `RECORD` \| `KNOW` \| `ACT` \| `GOVERN` |
| `journey_stage` | enum | `orientation` \| `decision` \| `action` \| `reflection` — **computed live per tenant, not stored** |
| `who` | enum | `tenant` \| `advocate` \| `agency` \| `researcher` \| `legal` \| `donor` |
| `why` | string | One-line rationale; used for querying, not shown to user |
| `provenance` | enum | `user_entered` \| `ocr_extracted` \| `system_computed` \| `semantically_retrieved` |
| `temporal_validity` | enum | `static` \| `time_bound` \| `event_triggered` |
| `subject_tags` | list[string] | Free-text tags for semantic matching (e.g. `["late fee", "MN", "lease clause"]`) |

`journey_stage` is computed at read time by `resolve_journey_stage()` from an `EncounterContext` (exposure count, has_derived_deadline, has_action_been_taken, is_reflection_phase). It is never stored as a static property of the object.

#### Page Envelope (`app/core/page_envelope.py`)
Page-level metadata, grammar-parallel to English sentence structure:

| Grammar role | Field | Purpose |
|---|---|---|
| Subject (noun) | `page_subject` | The single clear topic that leads the page |
| Objective (predicate) | `page_objectives` | What the page helps the tenant *do* (goals, not features) |
| Actions (verb phrases) | `page_actions` | Buttons/tasks, each backed by an Object Envelope |
| Prepositions (relational) | `page_relations` | How the subject connects to the tenant's timeline |
| Adjectives (qualifiers) | `page_state` | Honest, factual state descriptors only — no alarmist language |

#### Three-Layer Retrieval (ADR-0008 §2.2)
- **Layer 1 — Curated entries:** Human-written explanation blocks, each with four variant slots (trust/why, mechanics, reinforcement, minimal). Tagged with subject, jurisdiction, UPL risk tier, pillar, review_status (`beta` \| `vetted`).
- **Layer 2 — Semantic retrieval:** Currently metadata-only matching (see §4.3). Designed as a drop-in swap for real embedding similarity.
- **Layer 3 — Bounded local rephrasing (optional):** A small local model may adjust tone/length only. Never permitted to introduce a new fact. Source entry remains the attributable origin.
- **Guardrail:** If no Layer 1 entry matches well enough (confidence threshold), the orchestrator shows nothing rather than guessing. Silence is safer than a fabricated explanation.

#### Familiarity Tapering (ADR-0008 §2.4)
Explanation depth is a function of how many times a tenant has encountered that *object type*:

| Exposure | Behavior |
|---|---|
| 1st | Full explanation — trust/why-forward |
| 2nd–3rd | A different angle each time — mechanics, then brief reinforcement. Never verbatim repeat. |
| 4th+ | Collapses to minimal — real-time status only. Full explanation available on tap. |

#### Experience Token (ADR-0008 §2.7) — `app/core/experience_token.py`
Privacy-safe familiarity tracking. The exposure count is **never held by Semptify**. It lives as a small JSON file in the tenant's own connected cloud storage (same trust boundary as their documents). Semptify servers never hold it, never see it, and it isn't keyed to anything Semptify assigns.

Schema:
```json
{
  "exposure_tallies": {"object_type_a": 3, "object_type_b": 1},
  "intensity_level": 2,
  "token_version": 1
}
```

Pre-OAuth fallback: session-local state only. Resets on new device/session. Acceptable — only calibrates teaching depth, nothing load-bearing.

**Hard constraint:** No server-side tracking of any kind attached to a tenant identifier. Any implementation that introduces a Semptify-held table keyed to user ID for this purpose is out of spec.

#### Intensity Level (ADR-0008 §2.8)
A single scalar (0-3) stored inside the Experience Token. Tenant-controlled multiplier on momentum checkpoint frequency and explanation warmth. Default: 2 (Standard).

### 5.2 The Context Engine (`app/modules/context_engine/`)

The data layer that feeds the Information Orchestrator and the Page Composer.

#### Curated Explanation Entries (`explanation_entries.py`)
SQLAlchemy model, table `context_explanation_entries`:

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `entry_id` | String(32) | unique, indexed |
| `subject` | String(50) | indexed; one of 14 canonical subjects (see taxonomy) |
| `jurisdiction` | String(10) | indexed; default "MN" |
| `upl_risk_tier` | String(10) | LOW / MEDIUM / HIGH |
| `pillar` | String(10) | indexed; RECORD / KNOW / ACT / GOVERN |
| `review_status` | String(10) | indexed; BETA / VETTED |
| `variant_trust` | Text | explanation variant slot 1 |
| `variant_mechanics` | Text | explanation variant slot 2 |
| `variant_reinforcement` | Text | explanation variant slot 3 |
| `variant_minimal` | Text | explanation variant slot 4 |
| `created_at` | DateTime | |
| `updated_at` | DateTime | |

Composite index: `(subject, jurisdiction, pillar, review_status)`.

#### Verified Facts (`models.py` → `ContextFact`)
SQLAlchemy model, table `context_facts`:

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `subject` | String(50) | indexed |
| `jurisdiction` | String(10) | indexed; default "MN" |
| `claim` | Text | the factual claim |
| `source_url` | Text | required — no hallucination |
| `source_name` | String(100) | required |
| `citation` | Text | nullable |
| `canonical_value` | Text | nullable; for drift detection |
| `extraction_pattern` | Text | nullable; regex to extract value from source |
| `is_verified` | Boolean | default True |
| `verified_at` | DateTime | |
| `expires_at` | DateTime | indexed; nullable |
| `created_at` | DateTime | |

Composite index: `(subject, jurisdiction)`.

#### Tenant Stories (`models.py` → `TenantStory`)
Moderated, anonymized stories. Table `tenant_stories`. Not directly relevant to semantic retrieval but part of the same module.

#### Taxonomy (`taxonomy.py`)
14 canonical subjects: `eviction`, `repair`, `rent`, `lease`, `deposit`, `discrimination`, `safety`, `habitability`, `retaliation`, `small_claims`, `court_prep`, `evidence`, `timeline`, `landing`.

Each subject maps to an external API for fact gathering (MN Revisor, EPA ECHO, CourtListener, HUD, MN Courts). Two subjects (`evidence`, `timeline`) have no external API — guidance only. `landing` is for public marketing claims verified by the fact-check/freshness system.

#### Gatherer (`gatherer.py`)
Fetches fresh facts from external sources (MN statutes, EPA ECHO, CourtListener, HUD, MN Courts) and writes them into the `context_facts` cache via `upsert_fact()`. Every fact has a source URL — no hallucination.

#### Cache (`cache.py`)
PostgreSQL-backed fact cache. Facts expire after 7 days by default. Provides `get_facts()`, `get_verified_landing_facts()`, `upsert_fact()`, `prune_expired()`, `list_subjects_with_counts()`.

#### Verifier (`verifier.py`)
Checks that cached facts still resolve and content matches. Upgraded (ADR-0009) from HTTP HEAD to full GET + regex extraction + canonical value comparison. Mismatch → `is_verified=False` + freshness alert. Runs periodically via Render cron.

#### Retrieval (`retrieval.py`) — THE PLACEHOLDER
This is the file that would be modified or replaced by any semantic database solution.

Current implementation:
```python
LAYER2_CONFIDENCE_THRESHOLD = 0.75

async def retrieve_explanations(obj: ObjectEnvelope, *, jurisdiction="MN", limit=5) -> list[RetrievalResult]:
    # 1. Gather candidate entries by subject tag overlap
    # 2. Score each entry:
    #    - subject overlap: 0.4
    #    - jurisdiction match: 0.2
    #    - pillar match: 0.2
    #    - review_status vetted: 0.2
    # 3. Filter by score >= LAYER2_CONFIDENCE_THRESHOLD
    # 4. Sort highest-first, VETTED preferred
    # 5. Return top `limit` results

def select_tapered_variant(result: RetrievalResult, exposure_count: int) -> str:
    # 1st exposure → variant_mechanics
    # 2nd exposure → variant_trust
    # 3rd exposure → variant_reinforcement
    # 4th+ → variant_minimal
```

The `RetrievalResult` model includes a `score: float` field (0.0-1.0) that was designed to hold cosine similarity scores in the future. The interface (`retrieve_explanations` → `list[RetrievalResult]`) was deliberately shaped so the scoring function can be swapped without touching callers.

### 5.3 The Context Loop (`app/modules/context_loop/`)

A separate system that coexists with the Information Orchestrator. Do not confuse them.

- **What it does:** Tracks the tenant's *situation* — documents, deadlines, active issues, intensity score (0-100). Event-driven, continuous.
- **What the Information Orchestrator does:** Decides what to *say* about each object on a page, and how much. Render-time, per-object.
- **Integration point:** Context Loop tells the page "how urgent / what phase." Information Orchestrator tells the page "what to say and how much." They converge at the Page Composer.

The Context Loop is in-memory (`UserContext` dataclass, `ContextDataLoop` class with `contexts: dict[str, UserContext]`). It subscribes to EventBus events (document added, document processed, document classified, events extracted, case updated). It calculates intensity using `IntensityEngine` with base scores by event type, deadline multipliers, pattern escalation, rights-at-risk multipliers, and phase adjustments.

### 5.4 Database Layer

- **ORM:** async SQLAlchemy (`app/core/database.py`)
- **Dev:** SQLite via aiosqlite (`sqlite+aiosqlite:///./semptify.db`)
- **Prod:** PostgreSQL via asyncpg on Render (`postgresql+asyncpg://...`)
- **Connection pooling:** PostgreSQL uses AsyncAdaptedQueuePool (pool_size=5, max_overflow=10). SQLite uses NullPool.
- **Existing PostgreSQL extensions in use:** Full-text search via tsvector/tsquery (`app/core/postgres_fts.py`)
- **Table creation:** `init_db()` calls `Base.metadata.create_all()` with an opt-out set for tables requiring explicit Alembic migration.
- **Config:** `DATABASE_URL` env var. Auto-converts `postgres://` → `postgresql+asyncpg://`. SSL auto-detected (off for localhost, on for production).

### 5.5 Pilot Surfaces (where ADR-0008 is actually wired)

Two pilot surfaces are live on `main` (merged via PR #65, 2026-08-14):
- **Eviction Timeline** — `app/modules/eviction_timeline/envelopes.py` defines real Object/Page Envelopes.
- **Vault upload flow** — `app/modules/vault/envelopes.py` defines real Object/Page Envelopes.

Both have real backend events (for Live Event-Driven Narration) and real jurisdiction data to query against. Most pieces outside these two surfaces are built but not yet wired into day-to-day pages.

---

## 6. History — How We Got Here

| Date | Event |
|---|---|
| 2026-08-07 | **ADR-0007** written (BETA): OCR + Semantic Reasoning Privacy Model. Specifies client-side WASM/ONNX embedding generation for tenant documents. Status: BETA, not Accepted. |
| 2026-08-10 | **ADR-0008** written: Information Orchestrator. Originally designed Layer 2 retrieval to reuse ADR-0007's embedding pipeline. Preflight (todo-068) discovers the pipeline does not exist. ADR-0008 §2.2 revised to metadata-only matching. Embedding pipeline deferred as todo-077, "decoupled from the pilot's critical path." |
| 2026-07-28 | **todo-036 resolved:** `app/services/semantic_context_engine.py` built — rule-based date classification for OCR Pass 2. (This is the name-collision system. It has nothing to do with embeddings.) |
| 2026-08-14 | **ADR-0008 pilot surfaces** merged to main (PR #65): Eviction Timeline + Vault upload flow. |
| 2026-08-15 | **ADR-0009** written and Accepted: Fact-check/freshness system. Extends `ContextFact` with `canonical_value` and `extraction_pattern`. Upgrades verifier from HEAD to GET + pattern extraction. Promotes `data_freshness` to CORE tier. |
| 2026-08-18 | **Handoff:** Context Loop vs. Information Orchestrator investigation confirms they are coexisting, not a replacement chain. Page Composer confirmed as the integration point. |
| 2026-08-19 | **This audit** written. |

---

## 7. Why the Embedding Pipeline Was Never Built (Root Causes)

### Root Cause 1: ADR-0007's privacy model is unproven

ADR-0007 is BETA, not Accepted. Its entire decision hinges on client-side embedding generation via WASM/ONNX in the tenant's browser. Four success criteria for promotion to Accepted are all unchecked:

- [ ] Client-side path handles a defined minimum percentage of real test documents without falling back
- [ ] Fallback path confirmed, via logging audit, to retain zero document content after processing completes
- [ ] Classification confidence scores validated against human-reviewed ground truth on a test document set
- [ ] No open Tier-A-level privacy concerns remaining from a full review pass

The ADR names open questions that were never answered empirically:
- Does WASM/ONNX OCR + embedding perform acceptably on "the range of phones and browsers tenants actually use, especially older/lower-power devices"?
- How reliably does the system detect "client-side isn't going to work here" and route to the ephemeral server-side fallback?

Without these answers, the ADR cannot graduate from BETA, and the pipeline it specifies cannot be built.

### Root Cause 2: Two separable problems were conflated into one deferred task

ADR-0008 bundled two different embedding needs into "the embedding pipeline" (todo-077):

1. **Embedding curated content** — Layer 1 explanation entries, ContextFacts. This is Semptify's own human-authored content. No tenant PII. No privacy constraint. No dependency on ADR-0007's client-side path.
2. **Embedding tenant documents** — leases, notices, receipts. This is tenant PII. Hard privacy constraint: raw text never leaves the device. Fully dependent on ADR-0007's unproven client-side path.

When ADR-0007's pipeline proved unready, the entire bundle was deferred. The curated-content embedding need — which has no privacy dependency — was blocked by association.

### Root Cause 3: The naming collision obscures the problem

Three systems share the word "semantic":
- `semantic_context_engine.py` (rule-based date classifier, built, working)
- ADR-0007 (embedding pipeline for tenant documents, unbuilt)
- ADR-0008 §2.2 Layer 2 (semantic retrieval for curated content, built as placeholder)

Anyone hearing "the semantic engine isn't built" reasonably assumes `semantic_context_engine.py` is broken — but it's fine. Or they assume ADR-0007 and ADR-0008 Layer 2 are the same problem — but they aren't. The naming makes it hard to even discuss the problem clearly.

### Root Cause 4: Single-maintainer capacity

Semptify is maintained primarily by one person using AI tools. The ADR-0008 pilot was the priority — getting explanation retrieval working at all, even with metadata-only matching, was more valuable than perfecting the semantic engine. The deferral was a correct prioritization call, not an oversight. But it means the problem has now been deferred for ~12 days with no path forward articulated.

---

## 8. Hard Constraints

Any solution must satisfy ALL of these. Violating any one is a rejection.

### 8.1 Privacy — no server-side tenant tracking
- **Source:** ADR-0008 §3, Navigation Principle, storage-as-identity model.
- **Rule:** No server-side table keyed to a tenant identifier may hold familiarity/exposure state. The Experience Token lives in tenant-controlled cloud storage.
- **Implication for semantic DB:** Embeddings of *curated content* (Layer 1 entries, facts) are fine — that's Semptify's own content with no tenant PII. Embeddings of *tenant documents* require the ADR-0007 client-side privacy model, which is unproven.

### 8.2 Python 3.11.9 — non-negotiable
- **Source:** AGENTS.md, PROJECT_BIBLE.md.
- **Rule:** ALL code and dependencies must target Python 3.11.9. No 3.12+ dependencies. No upgrading Python.
- **Implication:** Any library must support 3.11.9. Check before proposing.

### 8.3 No live LLM / UPL risk
- **Source:** ADR-0008 §3, MOTIVATIONS.md.
- **Rule:** No component may perform live, unbounded LLM reasoning that could generate a new legal claim, fact, or recommendation. Everything shown is either human-authored content, a bounded rephrase, or real event narration.
- **Implication:** Semantic retrieval must surface existing human-reviewed content. It cannot generate new content at query time.

### 8.4 Silence beats fabrication
- **Source:** ADR-0008 §2.2 guardrail.
- **Rule:** If no match meets the confidence threshold, show nothing. A weak match is worse than no match.
- **Implication:** The confidence threshold is a safety mechanism, not just a quality filter.

### 8.5 Budget — donation-funded 501(c)(3)
- **Source:** Semptify bio, organizational structure.
- **Rule:** No per-query API costs for core functionality. No expensive managed services. One maintainer.
- **Implication:** Cloud-hosted vector databases with per-query pricing are likely impractical. Open-source, self-hostable solutions preferred.

### 8.6 No new identifier
- **Source:** ADR-0008 §2.7.
- **Rule:** Nothing about the semantic system may identify the tenant to Semptify any more than storing a document already does.
- **Implication:** Query-time embeddings of tenant input (if ever needed) must be transient and never persisted server-side against an identity.

### 8.7 Dev/prod parity
- **Source:** `app/core/database.py`, `app/core/config.py`.
- **Rule:** Dev runs SQLite. Prod runs PostgreSQL on Render. Solutions must work in both or degrade gracefully.
- **Implication:** A PostgreSQL-only extension (like pgvector) needs a SQLite fallback path for dev, or dev must accept reduced functionality.

### 8.8 Deterministic, auditable behavior
- **Source:** PROJECT_BIBLE.md §3, Integrity and Governance Compass.
- **Rule:** Prefer deterministic, auditable behavior over cleverness.
- **Implication:** Semantic retrieval results should be reproducible. If a tenant sees an explanation once, the same query should return the same result under the same conditions.

---

## 9. The Two Separable Problems

This is the key insight the audit exists to surface. An independent team should evaluate these independently.

### Problem A: Semantic retrieval over curated content

- **What:** Embed the Layer 1 explanation entries and ContextFacts (Semptify's own human-authored content) so that retrieval can match by meaning, not just by exact tag overlap.
- **Whose data:** Semptify's content. No tenant PII.
- **Privacy constraint:** None. This is public/internal content.
- **ADR-0007 dependency:** None. This does not touch tenant documents.
- **Scale:** Hundreds to low thousands of entries (14 subjects × jurisdictions × variants). Small.
- **Update frequency:** Low — entries are human-authored at authoring time. Embeddings can be precomputed.
- **Query pattern:** "Given this Object Envelope's subject_tags + context, find the best-matching explanation entries." Bounded, filtered by metadata (jurisdiction, pillar, review_status).
- **Current state:** Retrieval interface built (`retrieve_explanations` → `list[RetrievalResult]` with `score` field). Scoring function is metadata-only placeholder.

### Problem B: Semantic reasoning over tenant documents

- **What:** Embed tenant documents (leases, notices, receipts) for document-type classification and matching against a knowledge base.
- **Whose data:** Tenant's private documents. Contains PII (names, addresses, financial info).
- **Privacy constraint:** Hard. Raw document text and images never leave the tenant's device. Only embedding vectors cross to the server.
- **ADR-0007 dependency:** Total. This IS ADR-0007.
- **Scale:** Per-tenant, per-document. Unbounded growth.
- **Update frequency:** Per document upload.
- **Query pattern:** "What type of document is this? What dates/entities does it contain?" Classification + extraction.
- **Current state:** ADR-0007 BETA, never implemented. The rule-based `semantic_context_engine.py` handles date extraction without embeddings. Document-type classification is handled by other means.

**An independent team may propose:**
- Solving only Problem A and leaving Problem B to ADR-0007's eventual promotion.
- Solving both with a unified architecture.
- Solving Problem A in a way that also lays groundwork for Problem B.
- A completely different approach to either or both.
- Deciding that metadata-only matching is sufficient and neither problem needs embeddings.

---

## 10. What Has Been Considered

### 10.1 Metadata-only matching (current)
- **Status:** Built, working, tested.
- **Pros:** No dependencies, no privacy concerns, deterministic, fast.
- **Cons:** "late fee" won't match "penalty charge." Lexical tag overlap, not meaning-based. Requires manual tag curation. Doesn't scale to synonyms or paraphrased queries.
- **Verdict:** Sufficient for the pilot. Insufficient for scale — the team's own ADR says this is a placeholder.

### 10.2 pgvector on existing PostgreSQL (one prior team member's recommendation)
- **Status:** Recommended in a prior conversation. Not built.
- **Approach:** Add `vector(384)` column to `context_explanation_entries` and `context_facts`. Generate embeddings offline at authoring time with all-MiniLM-L6-v2. Query with cosine distance. Hybrid with existing metadata filters and PG FTS.
- **Pros:** Same database, no new service, no per-query cost, completes ADR-0008 §2.2's designed swap, Python 3.11.9 compatible.
- **Cons:** PostgreSQL extension — needs Render support for `CREATE EXTENSION vector`. SQLite has no `vector` type (dev parity issue). Only solves Problem A.
- **Note:** This is one option. The independent team should evaluate it alongside others.

### 10.3 Separate vector database (Qdrant, Chroma, Weaviate, Milvus)
- **Status:** Not proposed by the team. Listed here for completeness.
- **Approach:** Run a dedicated vector database alongside PostgreSQL.
- **Pros:** Purpose-built for vector search. Some have hybrid search built in.
- **Cons:** Splits source of truth (entries in PG, vectors in another service). Sync complexity. Another service to deploy/maintain for a donation-funded project with one maintainer. Overkill for hundreds-to-thousands of entries.

### 10.4 PostgreSQL Full-Text Search only
- **Status:** Already built (`app/core/postgres_fts.py`). In use for other features.
- **Approach:** Use tsvector/tsquery for retrieval instead of embeddings.
- **Pros:** Already exists. No new dependencies. PostgreSQL-native.
- **Cons:** Lexical, not semantic. "late fee" won't match "penalty charge." Stemming helps but doesn't solve synonym/paraphrase matching. This is what prompted ADR-0007 in the first place.

### 10.5 Client-side embeddings (ADR-0007 as written)
- **Status:** BETA, never implemented.
- **Approach:** WASM/ONNX in browser, all-MiniLM-L6-v2, embeddings never expose raw text.
- **Pros:** Solves Problem B's privacy constraint. Tenant documents never leave the device.
- **Cons:** Unproven on low-power devices. Complex client-side engineering. Four success criteria unchecked. Does not solve Problem A (curated content doesn't need client-side processing).

### 10.6 In-memory vector search (FAISS, Annoy)
- **Status:** Not proposed.
- **Approach:** Load embeddings into memory at startup, search with FAISS/Annoy.
- **Pros:** Fast. No database extension needed. Works in dev and prod.
- **Cons:** No persistence — rebuild on restart. Loses "source of truth in PostgreSQL" principle. Doesn't scale if entries grow significantly.

### 10.7 sqlite-vec for dev parity
- **Status:** Not proposed. Mentioned as a dev-fallback for pgvector.
- **Approach:** Use sqlite-vec extension in dev to match pgvector in prod.
- **Pros:** Dev/prod parity.
- **Cons:** Two code paths. sqlite-vec is less mature than pgvector.

### 10.8 Hybrid: metadata + FTS + embeddings
- **Status:** Not built. The natural endpoint of the current architecture.
- **Approach:** Combine metadata filtering (jurisdiction, pillar, review_status), PG FTS (keyword matching), and embedding cosine similarity (semantic matching) into a final ranked score.
- **Pros:** Best retrieval quality. Uses all three signals. Two of three already exist.
- **Cons:** More complex scoring. Needs all three systems working and tuned.

---

## 11. Open Questions for the Independent Team

These are the questions the current team has not answered. An independent team should address them directly.

### Architecture
1. **Should Problem A (curated content embeddings) and Problem B (tenant document embeddings) be solved with the same technology, or separated?** The current conflation is the root cause of the deferral. Is separation correct, or is there value in a unified approach?

2. **Is a vector database even necessary for Problem A?** The scale is hundreds to low thousands of entries across 14 subjects and a handful of jurisdictions. Could a simpler approach (expanded synonym dictionaries, curated tag taxonomies, FTS with thesaurus support) achieve the same quality without embeddings?

3. **If embeddings are used for Problem A, where should they live?** In PostgreSQL (pgvector), in a separate vector DB, in memory, or somewhere else? What are the trade-offs for a single-maintainer, donation-funded project?

4. **What embedding model is appropriate?** ADR-0007 chose all-MiniLM-L6-v2 (384 dims). Is that still the right choice? Should it be larger? Smaller? A different family? Does the choice matter if embeddings are precomputed at authoring time?

5. **Should the embedding be of the entry's subject tag, the full variant text, or a composite?** The entries have four variant slots. Which text gets embedded affects what the cosine similarity actually measures.

### Privacy
6. **If Problem A is separated from Problem B, does any privacy constraint apply to Problem A at all?** The curated content is Semptify's own, not tenant data. Is there any reason embeddings of curated content should be treated differently from any other server-side content?

7. **If query-time embeddings of tenant input are ever needed (e.g., embedding the tenant's question to match against curated entries), what privacy rules apply?** The tenant's question is not a document, but it is tenant input. Is a transient, never-persisted embedding acceptable? Does this need ADR-level treatment?

### Dev/Prod parity
8. **How should the SQLite dev environment handle a PostgreSQL-only feature like pgvector?** Options: (a) skip embeddings in dev, fall back to metadata matching; (b) use sqlite-vec; (c) require PostgreSQL for dev too; (d) something else.

### Operational
9. **Who generates the embeddings and when?** At authoring time (when a Layer 1 entry is created/updated)? In a batch job? On-demand? Does this affect the choice of model or infrastructure?

10. **How are embeddings kept in sync with content changes?** If a Layer 1 entry's variant text is edited, does the embedding need regeneration? What's the update workflow?

11. **What happens when the embedding model is upgraded?** All stored embeddings become stale. What's the migration path? Does this affect the choice of storage (re-embeddable from source text vs. locked-in)?

12. **What is the confidence threshold calibration process?** ADR-0008 §5 #3 set `LAYER2_CONFIDENCE_THRESHOLD = 0.75` as a starting value. How should it be calibrated for real cosine scores? What's the feedback loop?

### Scope
13. **Is the current metadata-only matching actually insufficient?** Has anyone measured the gap? Are there real cases where tenants got the wrong explanation (or no explanation) because "late fee" didn't match "penalty charge"? Or is this a theoretical concern?

14. **Should the semantic system also serve the Context Loop, or only the Information Orchestrator?** The Context Loop's intensity scoring is currently rule-based (base scores × multipliers). Could semantic matching improve issue classification or risk factor detection? Or is that a separate problem?

15. **What is the migration path from the current metadata-only retrieval to whatever is chosen?** The interface (`retrieve_explanations` → `list[RetrievalResult]`) was designed for a drop-in swap. Is that still the right integration point, or should the interface change too?

---

## 12. Key Files Reference

### Core schemas
- `app/core/context_envelope.py` — Object Envelope schema + journey stage resolver
- `app/core/page_envelope.py` — Page Envelope schema
- `app/core/experience_token.py` — Privacy-safe familiarity tracking (tenant cloud storage)

### Context Engine (the data + retrieval layer)
- `app/modules/context_engine/models.py` — `ContextFact`, `TenantStory` SQLAlchemy models
- `app/modules/context_engine/explanation_entries.py` — `ContextExplanationEntry` SQLAlchemy model
- `app/modules/context_engine/retrieval.py` — **Layer 2 retrieval (the placeholder to swap)**
- `app/modules/context_engine/taxonomy.py` — 14 canonical subjects + external API mapping
- `app/modules/context_engine/gatherer.py` — External fact fetching
- `app/modules/context_engine/cache.py` — PostgreSQL fact cache (CRUD + TTL)
- `app/modules/context_engine/verifier.py` — Fact freshness verification (GET + pattern extraction)

### Context Loop (separate system — situational state)
- `app/modules/context_loop/service.py` — `ContextDataLoop`, `IntensityEngine`, `UserContext`, `ContextEvent`

### Database
- `app/core/database.py` — async SQLAlchemy engine, SQLite/PostgreSQL dual support
- `app/core/config.py` — `DATABASE_URL` resolution
- `app/core/postgres_fts.py` — PostgreSQL full-text search (already in use)

### ADRs
- `docs/adr/0007-ocr-semantic-reasoning-privacy.md` — BETA, never implemented
- `docs/adr/0008-information-orchestrator.md` — Accepted, pilot surfaces live
- `docs/adr/0009-fact-check-freshness-system.md` — Accepted, live

### Name-collision system (not related to this problem)
- `app/services/semantic_context_engine.py` — Rule-based date classifier for OCR Pass 2

### Pilot surfaces (where ADR-0008 is wired)
- `app/modules/eviction_timeline/envelopes.py` — Object/Page Envelopes for eviction timeline
- `app/modules/vault/envelopes.py` — Object/Page Envelopes for vault upload

### Tests
- `tests/test_information_orchestrator_pilot.py` — Pilot test coverage

### Governance
- `PROJECT_BIBLE.md` — Canonical doc hierarchy and governance
- `AGENTS.md` — Python 3.11.9 mandate, Known Failure Registry, module contract rules
- `docs/MOTIVATIONS.md` — Foundational motivations, language rules, design principles

---

## 13. Glossary

| Term | Definition |
|---|---|
| **Object Envelope** | Per-object metadata that tells the system what an object is, why it exists, and who it's for. |
| **Page Envelope** | Page-level metadata: subject, objectives, actions, relations, state. |
| **Layer 1** | Human-written, versioned explanation entries with four variant slots. |
| **Layer 2** | Retrieval mechanism that finds the best Layer 1 entry for a given object. Currently metadata-only. |
| **Layer 3** | Optional bounded local rephrasing of a Layer 1 entry (tone/length only, no new facts). |
| **Familiarity Tapering** | Reducing explanation depth based on how many times the tenant has seen this object type. |
| **Experience Token** | Privacy-safe JSON file in tenant cloud storage tracking exposure counts and intensity preference. |
| **Context Loop** | Event-driven system tracking the tenant's situation (documents, deadlines, intensity). Separate from the Information Orchestrator. |
| **Context Engine** | Data layer: curated explanation entries, verified facts, tenant stories, retrieval, gathering, verification. |
| **UPL risk tier** | Unauthorized Practice of Law risk level (LOW/MEDIUM/HIGH). Determines whether content needs attorney review. |
| **Storage-as-identity** | Architectural trust model: tenant's cloud storage IS their identity. No passwords, no server-side user tables. |
| **Information Orchestrator** | The system defined by ADR-0008: gives every object and page structured context and resolves it into right-sized explanation. |
| **Semantic Context Engine** | Name-collision system. Rule-based date classifier for OCR text. NOT an embedding engine. |
| **pgvector** | PostgreSQL extension for vector similarity search. One possible solution for Problem A. |
| **all-MiniLM-L6-v2** | A small sentence embedding model (384 dimensions) chosen by ADR-0007. |
| **WASM/ONNX** | Browser-based runtime for running ML models client-side. ADR-0007's chosen path for tenant document privacy. |

---

## 14. What This Audit Does NOT Do

- It does not prescribe a solution. The independent team should propose their own.
- It does not evaluate ADR-0007's privacy model. That is a separate review.
- It does not assess the quality of existing Layer 1 content. That is a content review, not an architecture review.
- It does not address the Context Loop's in-memory state model. That is a separate scalability concern.
- It does not cover the Page Composer or UI Composer architecture. Those are page rendering systems, not context storage systems.

---

*This audit was compiled from direct reading of the Semptify codebase, ADRs, BUILD_STATE, ACTIVE_CONTEXT, and handoff documents. No code was changed. No runtime verification was performed (docs-only deliverable).*
