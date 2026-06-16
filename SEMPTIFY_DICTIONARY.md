# SEMPTIFY DICTIONARY
# Canonical definitions for every structural term used in this codebase.
# When in doubt, look here first. When a term isn't here, add it.
# Last updated: 2026-06-16

---

## Core Concepts

### App
The single running FastAPI process. There is one App. It starts, loads modules,
and serves all HTTP requests. File: `app/main.py`.

### System
Everything that makes Semptify work — the App, the database, the storage
providers, the session layer, background workers, and all modules combined.
"The system" refers to the whole. "The app" refers to the running process.

---

## Structural Units (smallest to largest)

### Function
A Python `def` or `async def`. A single, named, callable unit of logic.
Does one thing. Has no HTTP route. Has no database table. Examples:
- `utc_now()` — returns current UTC datetime
- `parse_user_id()` — extracts role and provider from a signed user ID
- `get_document_registry()` — returns the singleton registry instance

### Service
A Python class or collection of functions that performs a specific domain
operation. No HTTP routes. No UI. Called by routers or other services.
Lives in `app/services/`. Examples:
- `VaultUploadService` — uploads, certifies, and indexes a document
- `DocumentRegistry` — hashes, registers, and tracks documents
- `TokenManager` — stores and retrieves OAuth tokens

### Router
A FastAPI `APIRouter` that defines HTTP endpoints (GET, POST, etc.) for one
domain. A router is the HTTP surface of a module. It calls services. It does
not contain business logic itself. Lives inside a module folder as `router.py`.

### Module
A module is one of two types. Every module in Semptify is one or the other.
Never mix them. Never blur the line.

#### Pipeline Module
A set of instructions that prepares output for another module or the DB.
No UI. No direct user interaction. Always running. Part of the engine.

Rules:
- Never hot-swapped or user-loadable
- Lives in `app/services/` or as a service-only module in `app/modules/`
- Called BY feature modules — never calls feature modules back
- Failure here is a system failure, not a user feature being unavailable

Examples: `vault_upload_service`, `document_registry`, `certification`,
`extraction`, `context_loop`, `token_manager`

#### Feature Module
A complete, self-contained user capability. Has UI, routes, and backend logic.
Can be loaded per user, per role, or per session. Can be overlaid in dev mode.

Rules:
- Can be loaded or unloaded without touching other modules or the engine
- Has a single HTTP entry point (`router.py`)
- Talks DOWN to pipeline modules — never sideways to other feature modules
- Lives in `app/modules/` as a full folder (router + service + templates)
- Absence of a feature module = feature unavailable. App still runs fine.

Examples: `case_builder`, `fems`, `timeline`, `court_forms`,
`eviction_defense`, `onboarding`, `admin_console`

#### The One Rule That Protects Everything
```
USER
  ↓
Feature Module
  ↓
Pipeline Module
  ↓
Database / Storage / External APIs
```
Feature modules call DOWN to pipeline modules.
Pipeline modules NEVER call UP to feature modules.
Feature modules NEVER call sideways to other feature modules directly.

### Tier
A named group of modules that form a product boundary. Tiers are declared in
`app/core/product_manifest.py`. A tier can be enabled or disabled as a unit.

| Tier | Purpose |
|------|---------|
| `CORE` | Essentials — always on. Vault, onboarding, auth, tenant home. |
| `EXTENDED` | Legal tools — eviction defense, court forms, case builder. |
| `ADVOCATE` | Advocate network — document delivery, collaboration. |
| `ADMIN` | Admin console, analytics, audit logs, batch ops. |
| `RESEARCH` | AI intelligence — extraction, crawlers, recognition. |
| `DEV` | Internal tools — page editor, setup wizard, dev helpers. |

### Capability
A specific feature a user can access, regardless of how it's implemented.
Capabilities are what the user sees ("I can generate a letter", "I can view
my timeline"). A capability maps to one or more modules. A user's active
capability set is what determines their experience.

**Capabilities are user-facing. Modules are developer-facing.**

### Capability Set
The collection of capabilities available to a specific user at a specific time.
Determined by: their role defaults + any capabilities they've activated or
been granted. Stored in the DB against the user.

### Overlay
An experimental or role-specific module that attaches on top of the running
system without modifying it. An overlay:
- Can only ADD new routes, never replace existing ones
- Is flagged `overlay=True` in the manifest
- Is session-scoped for dev use (stripped when the dev session ends)
- Is role-scoped for production use (e.g. advocate-only features)

Used for: dev testing without affecting prod, beta features, per-client
customization without forking the codebase.

---

## User & Role Concepts

### User
A registered person with a signed `user_id` cookie, a storage provider
connected, and a vault initialized. Stored in the `users` table.

### Role
A user's primary function in the system. Determines their default capability
set and which pages they can reach.

| Role | Description |
|------|-------------|
| `tenant` | A renter seeking housing rights help |
| `advocate` | A person helping one or more tenants |
| `manager` | A property manager with conditional tenant access |
| `admin` | System administrator with elevated access (time-limited) |

### Gate
A binary checkpoint in the onboarding flow. A gate is either passed or not.
Once passed, it stays passed. Gates live in `app/modules/onboarding/gates.py`.

| Gate | Meaning |
|------|---------|
| `storage_connected` | OAuth completed, cloud storage provider linked |
| `vault_initialized` | Vault folders created, user is fully activated |
| `document_uploaded` | First document uploaded and certified |

**Gates are not capabilities.** Gates are one-time onboarding checkpoints.
Capabilities are ongoing access rights.

### Relationship
A link between two users that grants one access to the other's data under
defined conditions. Stored in `user_relationships` table. Examples:
- Advocate → Tenant (advocate can view tenant's documents)
- Admin → Any (admin override, time-limited)

---

## Storage Concepts

### Vault
A user's private document storage structure in their cloud provider (Google
Drive, Dropbox, OneDrive). The vault is a set of folders the user owns.
Semptify creates and organizes them; the user retains full ownership.

### Vault Folder
One named folder inside the vault. Created at onboarding (7 core folders)
or on-demand when a feature needs it.

### Vault ID (`vault_id`)
A unique identifier for a specific uploaded document instance in the vault.
Format: `doc_XXXXXXXXXXXXXXXXX`. Not the same as a file path.

### Registry ID (`registry_id`)
A tamper-proof document identity assigned at upload time. Proves the document
existed at that moment and has not been altered since.
Format: `SEM-YYYY-NNNNNN-XXXX`.

### Certification
The process of hashing a document, registering it, and writing a compliance
record to PostgreSQL. Every upload is certified. A `CertificationEvent` row
is written for every outcome — pass or fail.

---

## Infrastructure Concepts

### SSOT (Single Source of Truth)
The principle that every piece of data or logic has exactly one authoritative
location. In Semptify: navigation paths come from `navigation.py`, vault paths
from `vault_paths.py`, module declarations from `product_manifest.py`. Nothing
is hardcoded in two places.

### Gate System
The mechanism that controls what a user can access during and after onboarding.
Implemented as DB-backed boolean flags checked by middleware.

### Hot Swap
Replacing or attaching a module at runtime without restarting the server.
Target capability for the overlay system — dev attaches a module, tests it,
detaches it, and prod never knew it happened.

### Dev Node
A dev-mode session where overlay modules are active. The running app is
identical to production except the overlay layer is mounted on top.
Used for: testing new modules, debugging live issues, building new features
against real data without a separate staging server.

### Session
One authenticated user's active connection to the system. Identified by
signed cookies. Holds: user_id, provider, role, active capabilities.

### Token
An OAuth access token from a storage provider (Google Drive, Dropbox, etc.).
Cached in Redis. Used to read/write the user's vault.

---

## Data Concepts

### Model
A SQLAlchemy class that maps to a PostgreSQL table. Lives in `app/models/models.py`.
A model is a DB table definition. It is not a service. It is not a router.

### Schema
A Pydantic class that validates and serializes data going into or out of an
HTTP endpoint. Lives near the router that uses it. Not the same as a model.

### Migration
An Alembic script that modifies the database schema (adds tables, columns, etc.).
Every schema change requires a migration. Never modify tables by hand.

---

---

## Key Pipeline Modules — How They Work

### Context Loop (`app/modules/context_loop/`)
The analyst. Tracks everything happening to one user and maintains their live
situational picture. Always running. Feeds every feature module that needs to
know how urgent a tenant's situation is.

Flow: `INPUT → PROCESS → INTENSITY → OUTPUT → LEARN`

- Receives events: document uploaded, deadline found, issue reported
- Scores urgency 0-100 (eviction notice = 85, court summons = 90)
- Applies multipliers: 3 days to court → ×1.25 → score hits CRITICAL
- Flags rights at risk, generates predictions, recommends next actions
- Publishes `UI_REFRESH_NEEDED` so the dashboard updates in real time

**Answers:** "How bad is this tenant's situation right now, and what next?"

### Positronic Brain (`app/services/positronic_brain.py`)
The coordinator. Connects all modules so they can talk without knowing about
each other. Runs multi-step workflows. Tracks module dependencies.

- Modules register with the Brain on startup
- Brain maintains a dependency graph (eviction module needs documents + timeline + calendar)
- When something happens, Brain fires events to every subscribed module in order
- Runs full workflows: upload → classify → extract → timeline → defenses → court forms
- Shared state store so all modules see the same picture

**Answers:** "When something happens, which modules need to know, and in what order?"

### How They Fit Together
```
User uploads document
        ↓
Vault Upload Service     (certifies, stores — pipeline)
        ↓
Positronic Brain         (fires events, runs workflow — pipeline)
        ↓         ↓          ↓           ↓
   Classifier  Extractor  Timeline   Calendar
        ↓
Context Loop             (scores urgency, updates user picture — pipeline)
        ↓
Feature Modules          (case_builder, eviction_defense, court_forms...)
        ↓
User sees updated dashboard with urgency score + recommended actions
```

### Where The Capability System Plugs In
The Brain knows which modules are connected (dependency graph).
The Capability System tells the Brain which modules THIS user has active.
When a tenant without `eviction_defense` uploads an eviction notice, the Brain
skips that step — not in their capability set. No code changes needed in the
Brain. The capability layer gates what the Brain coordinates, per user.

---

## What Is NOT a Module

To be explicit, these things are **not** modules:

| Term | What it actually is |
|------|---------------------|
| A single `.py` file | A file, possibly a service or utility |
| A Pydantic schema | A data shape definition |
| A SQLAlchemy model | A DB table definition |
| A FastAPI `Depends()` | A dependency injection function |
| A middleware | A request/response interceptor |
| A background task | An async job, not user-facing |
