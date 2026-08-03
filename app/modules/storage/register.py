"""Storage module registration helper — FunctionGroupContracts.

The storage module is the cloud storage layer. It handles OAuth flows
(connect, callback), provider listing, session management, role switching,
logout, integrity proofs, and function tokens. It is NOT the vault — the
vault stores documents; storage manages the connection to the cloud.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


# --- Session & Status ---

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_session_status",
    title="Storage Session Status (SSOT)",
    description=(
        "CANONICAL session status check. Returns whether the user has a "
        "valid session, storage provider, and vault. Used by UI gates."
    ),
    inputs=("semptify_session?",),
    outputs=("authenticated", "has_storage", "user_id"),
    dependencies=("app.modules.storage.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_entry",
    title="Storage Entry (SSOT)",
    description=(
        "CANONICAL storage entry point. Redirects to the appropriate page "
        "based on the user's state: no cookie ▸ welcome, no storage ▸ "
        "providers, has storage ▸ home."
    ),
    inputs=("semptify_uid?"),
    outputs=("redirect",),
    dependencies=("app.modules.storage.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_status",
    title="Storage Status (SSOT)",
    description=(
        "CANONICAL storage connection status. Returns provider, connected "
        "status, and token validity. Used by the storage status widget."
    ),
    inputs=("semptify_uid?"),
    outputs=("connected", "provider", "token_valid"),
    dependencies=("app.modules.storage.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_session_info",
    title="Storage Session Info (SSOT)",
    description=(
        "CANONICAL session information. Returns user_id, role, provider, "
        "and session metadata. Used by the frontend for user context."
    ),
    inputs=("semptify_uid?"),
    outputs=("user_id", "role", "provider", "session_meta"),
    dependencies=("app.modules.storage.router",),
    deterministic=True,
))

# --- OAuth ---

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_connect",
    title="Storage Connect (SSOT)",
    description=(
        "CANONICAL initiate OAuth flow for a storage provider. Redirects "
        "to the provider's authorization page."
    ),
    inputs=("role", "semptify_uid?"),
    outputs=("redirect",),
    dependencies=("app.modules.storage.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_oauth_initiate",
    title="Storage OAuth Initiate (SSOT)",
    description=(
        "CANONICAL OAuth initiation for a specific provider. Builds the "
        "auth URL with correct scopes and state, redirects to provider."
    ),
    inputs=("provider", "semptify_uid?"),
    outputs=("redirect",),
    dependencies=("app.modules.storage.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_oauth_callback",
    title="Storage OAuth Callback (SSOT)",
    description=(
        "CANONICAL OAuth callback handler. Exchanges the auth code for "
        "tokens, stores them, creates/updates the user record, and "
        "redirects to the next step (vault setup or home)."
    ),
    inputs=("provider", "code", "state"),
    outputs=("redirect", "user_id"),
    dependencies=("app.modules.storage.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_providers_list",
    title="Storage Providers List (SSOT)",
    description=(
        "CANONICAL list of available storage providers. Returns provider "
        "names, display info, and OAuth URLs. Used by the provider "
        "selection page."
    ),
    inputs=("semptify_uid?"),
    outputs=("providers",),
    dependencies=("app.modules.storage.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_providers_json",
    title="Storage Providers JSON (SSOT)",
    description=(
        "CANONICAL JSON list of storage providers. Returns provider codes "
        "and metadata as JSON for API consumers."
    ),
    inputs=("semptify_uid?"),
    outputs=("providers",),
    dependencies=("app.modules.storage.router",),
    deterministic=True,
))

# --- Device & Session Management ---

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_rehome",
    title="Storage Rehome Device (SSOT)",
    description=(
        "CANONICAL device rehoming. Allows a user to move their account to "
        "a new device by re-issuing the user cookie and syncing the session."
    ),
    inputs=("user_id",),
    outputs=("redirect", "synced"),
    dependencies=("app.modules.storage.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_user_lookup",
    title="Storage User Lookup (SSOT)",
    description=(
        "CANONICAL user lookup by user_id. Returns the user record if found. "
        "Used for session restoration and device sync."
    ),
    inputs=("user_id",),
    outputs=("found", "user"),
    dependencies=("app.modules.storage.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_session_restore",
    title="Storage Session Restore (SSOT)",
    description=(
        "CANONICAL session restoration. Restores a user's session from a "
        "user_id, re-issuing the auth cookie. Used for cross-device sync."
    ),
    inputs=("user_id",),
    outputs=("success", "user_id"),
    dependencies=("app.modules.storage.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_prepare_reconnect",
    title="Storage Prepare Reconnect (SSOT)",
    description=(
        "CANONICAL prepare for storage reconnection. Clears the expired "
        "token and prepares the user for a fresh OAuth flow without "
        "losing their vault or data."
    ),
    inputs=("semptify_uid?"),
    outputs=("prepared",),
    dependencies=("app.modules.storage.router",),
    deterministic=False,
))

# --- Role & Logout ---

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_switch_role",
    title="Storage Switch Role (SSOT)",
    description=(
        "CANONICAL role switching. Changes the user's role and re-issues "
        "the auth cookie with the new role. Used by the role switcher UI."
    ),
    inputs=("role", "semptify_uid?"),
    outputs=("success", "new_role"),
    dependencies=("app.modules.storage.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_logout",
    title="Storage Logout (SSOT)",
    description=(
        "CANONICAL logout. Clears the auth cookie, revokes the session, "
        "and redirects to the welcome page."
    ),
    inputs=("semptify_uid?"),
    outputs=("success",),
    dependencies=("app.modules.storage.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_logout_reset",
    title="Storage Logout Reset (SSOT)",
    description=(
        "CANONICAL GET logout reset. Clears a stale semptify_uid cookie "
        "and redirects to provider selection. Used when the cookie is "
        "corrupt or expired."
    ),
    inputs=(),
    outputs=("redirect",),
    dependencies=("app.modules.storage.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_regenerate_rehome",
    title="Storage Regenerate Rehome (SSOT)",
    description=(
        "CANONICAL regenerate rehome token. Issues a new rehome token for "
        "the user, allowing them to rehome to a new device."
    ),
    inputs=("semptify_uid?"),
    outputs=("rehome_token",),
    dependencies=("app.modules.storage.router",),
    deterministic=False,
))

# --- Integrity & Certificates ---

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_integrity_hash",
    title="Storage Integrity Hash (SSOT)",
    description=(
        "CANONICAL document content hashing. Returns SHA-256 hash of the "
        "provided content for integrity verification."
    ),
    inputs=("content", "semptify_uid?"),
    outputs=("hash",),
    dependencies=("app.modules.storage.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_integrity_proof",
    title="Storage Integrity Proof (SSOT)",
    description=(
        "CANONICAL create a cryptographic proof for document content. "
        "Returns the proof data with hash, timestamp, and action."
    ),
    inputs=("content", "action?", "semptify_uid?"),
    outputs=("proof",),
    dependencies=("app.modules.storage.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_integrity_verify",
    title="Storage Integrity Verify (SSOT)",
    description=(
        "CANONICAL verify document integrity against a proof. Returns "
        "whether the content matches the proof and the proof is valid."
    ),
    inputs=("content", "proof_data", "semptify_uid?"),
    outputs=("valid", "verification"),
    dependencies=("app.modules.storage.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_integrity_timestamp",
    title="Storage Integrity Timestamp (SSOT)",
    description=(
        "CANONICAL current legal timestamp with cryptographic proof. "
        "Returns the current UTC timestamp and a proof of issuance."
    ),
    inputs=(),
    outputs=("timestamp", "proof"),
    dependencies=("app.modules.storage.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_certificate_generate",
    title="Storage Certificate Generate (SSOT)",
    description=(
        "CANONICAL generate a SEMPTIFY certificate for a document. Returns "
        "the certificate with ID, hash, timestamp, and signer info."
    ),
    inputs=("document_name", "content?", "semptify_uid?"),
    outputs=("certificate_id", "certificate"),
    dependencies=("app.modules.storage.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_certificate_html",
    title="Storage Certificate HTML (SSOT)",
    description=(
        "CANONICAL generate a certificate as HTML for display. Returns "
        "the certificate rendered as HTML for the tenant to view/print."
    ),
    inputs=("document_name", "content?", "semptify_uid?"),
    outputs=("html",),
    dependencies=("app.modules.storage.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_certificate_verify",
    title="Storage Certificate Verify (SSOT)",
    description=(
        "CANONICAL verify a SEMPTIFY certificate by ID. Returns whether "
        "the certificate is valid and its metadata."
    ),
    inputs=("certificate_id", "code?"),
    outputs=("valid", "certificate"),
    dependencies=("app.modules.storage.router",),
    deterministic=True,
))

# --- Function Tokens ---

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_function_token_issue",
    title="Storage Function Token Issue (SSOT)",
    description=(
        "CANONICAL issue a function-scoped token for a user. Allows "
        "limited-scope access to specific APIs without full session."
    ),
    inputs=("semptify_uid?"),
    outputs=("token", "expires_at"),
    dependencies=("app.modules.storage.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_function_token_verify",
    title="Storage Function Token Verify (SSOT)",
    description=(
        "CANONICAL verify a function-scoped token. Returns whether the "
        "token is valid and its associated user_id."
    ),
    inputs=("token", "refresh?"),
    outputs=("valid", "user_id"),
    dependencies=("app.modules.storage.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="storage",
    group_name="storage_validate_token",
    title="Storage Validate and Refresh Token (SSOT)",
    description=(
        "CANONICAL validate the user's storage token and refresh if expired. "
        "Returns whether the token is valid and the provider."
    ),
    inputs=("semptify_uid?"),
    outputs=("valid", "provider"),
    dependencies=("app.modules.storage.router",),
    deterministic=False,
))
