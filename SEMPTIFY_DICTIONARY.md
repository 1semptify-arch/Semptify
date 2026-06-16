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
A self-contained folder under `app/modules/` that bundles:
- A `router.py` (HTTP endpoints)
- A `service.py` or equivalent (business logic)
- Optionally: models, schemas, templates, static files

A module owns one domain. It does not reach into other modules.
It declares its dependencies explicitly. Examples:
- `app/modules/fems/` — Forensic Evidence Management
- `app/modules/onboarding/` — New user setup flow
- `app/modules/case_builder/` — Build a legal case file

**A module is NOT a function. A module is NOT a service.**
A module = router + service + everything needed for one domain to work.

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
