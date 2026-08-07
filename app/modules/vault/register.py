"""Vault module registration helper — FunctionGroupContracts.

The vault is the RECORD pillar's storage layer. It stores, serves, and certifies
tenant documents in their own cloud storage. It does NOT intake from the UI
(intake.py is the one door in). These contracts describe the vault's capabilities
for the Page Composer and module orchestration system.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

# --- Document Storage & Retrieval ---

register_function_group(FunctionGroupContract(
    module="vault",
    group_name="vault_upload",
    title="Vault Upload (SSOT)",
    description=(
        "CANONICAL internal/service upload endpoint. Stores a document in the "
        "user's cloud storage with SHA-256 hash, certificate, and metadata. "
        "Called by VaultUploadService — NOT directly from the tenant UI. "
        "UI uploads must go through /api/intake/upload/auto."
    ),
    inputs=("file", "user_id", "document_type?", "description?", "tags?"),
    outputs=("document_id", "certificate_id", "sha256_hash", "storage_path"),
    dependencies=("app.modules.vault.router", "app.services.vault_upload_service"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="vault",
    group_name="vault_list_documents",
    title="Vault List Documents (SSOT)",
    description=(
        "CANONICAL list of documents in the user's vault. Supports filtering by "
        "document_type. Returns document summaries with id, filename, type, "
        "size, and timestamps. Used by the tenant documents page."
    ),
    inputs=("user_id", "document_type?"),
    outputs=("documents", "total"),
    dependencies=("app.modules.vault.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="vault",
    group_name="vault_download_document",
    title="Vault Download Document (SSOT)",
    description=(
        "CANONICAL download of a specific document by ID from the user's cloud "
        "storage. Returns the file stream with correct content-type. "
        "Used by the tenant documents page for file retrieval."
    ),
    inputs=("document_id", "user_id"),
    outputs=("file_stream", "filename", "mime_type"),
    dependencies=("app.modules.vault.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="vault",
    group_name="vault_get_certificate",
    title="Vault Get Certificate (SSOT)",
    description=(
        "CANONICAL retrieval of a document's chain-of-custody certificate. "
        "Returns the SEMPTIFY certificate with SHA-256, upload timestamp, "
        "storage path, and version. Used for evidence integrity verification."
    ),
    inputs=("document_id", "user_id"),
    outputs=("certificate_id", "sha256", "certified_at", "storage_path"),
    dependencies=("app.modules.vault.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="vault",
    group_name="vault_delete_document",
    title="Vault Delete Document (SSOT)",
    description=(
        "CANONICAL deletion of a document from the user's vault. Tenant-only. "
        "Removes the file and its certificate from cloud storage. "
        "Legal/advocate roles cannot delete (read-only vault access)."
    ),
    inputs=("document_id", "user_id"),
    outputs=("status",),
    dependencies=("app.modules.vault.router",),
    deterministic=False,
))

# --- Vault Setup & Verification ---

register_function_group(FunctionGroupContract(
    module="vault",
    group_name="vault_init",
    title="Vault Initialize (SSOT)",
    description=(
        "CANONICAL creation of the Semptify vault folder structure in the "
        "user's cloud storage. Called during onboarding after storage OAuth. "
        "Creates .Semptify5.0/ root and all canonical subfolders."
    ),
    inputs=("user_id", "provider"),
    outputs=("ok", "message"),
    dependencies=("app.modules.vault.router", "app.sdk.vault"),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="vault",
    group_name="vault_verify",
    title="Vault Verify (SSOT)",
    description=(
        "CANONICAL verification that the vault folder structure is accessible "
        "in the user's cloud storage. Returns per-folder status. "
        "Empty folders are valid (only failure is inaccessible/missing)."
    ),
    inputs=("user_id", "provider"),
    outputs=("ok", "folders"),
    dependencies=("app.modules.vault.router", "app.sdk.vault"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="vault",
    group_name="vault_status",
    title="Vault Status (SSOT)",
    description=(
        "CANONICAL lightweight check that the user is authenticated and has a "
        "storage provider configured. Used by UI gates and onboarding flow."
    ),
    inputs=("user_id",),
    outputs=("ok", "provider"),
    dependencies=("app.modules.vault.router",),
    deterministic=True,
))

# --- Sidebar (Quick Upload from any page) ---

register_function_group(FunctionGroupContract(
    module="vault",
    group_name="vault_sidebar_files",
    title="Vault Sidebar Files (SSOT)",
    description=(
        "CANONICAL list of recent files for the persistent vault sidebar. "
        "Returns a compact list for display in the side panel on any tenant page."
    ),
    inputs=("user_id",),
    outputs=("files",),
    dependencies=("app.modules.vault.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="vault",
    group_name="vault_sidebar_upload",
    title="Vault Sidebar Upload (SSOT)",
    description=(
        "CANONICAL quick upload from the persistent sidebar. Accepts multiple "
        "files, stores them in the vault, returns per-file status. "
        "This is the 'Add Record' button on every tenant page."
    ),
    inputs=("files", "user_id"),
    outputs=("uploaded", "errors"),
    dependencies=("app.modules.vault.router", "app.services.vault_upload_service"),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="vault",
    group_name="vault_sidebar_stats",
    title="Vault Sidebar Stats (SSOT)",
    description=(
        "CANONICAL vault statistics for sidebar display. Returns counts by "
        "document type, total size, and last upload timestamp."
    ),
    inputs=("user_id",),
    outputs=("total_documents", "total_size", "by_type", "last_upload"),
    dependencies=("app.modules.vault.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="vault",
    group_name="vault_sidebar_search",
    title="Vault Sidebar Search (SSOT)",
    description=(
        "CANONICAL search across the user's vault documents. Searches filename, "
        "document_type, description, and tags. Returns matching summaries."
    ),
    inputs=("query", "user_id"),
    outputs=("results",),
    dependencies=("app.modules.vault.router",),
    deterministic=True,
))
