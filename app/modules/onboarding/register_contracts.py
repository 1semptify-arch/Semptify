"""Onboarding module registration helper — FunctionGroupContracts.

The onboarding module is the entry gate. It walks a new tenant from role
selection → storage OAuth → vault setup → completion. Gate-driven, not
flag-driven. Storage connection is mandatory — no skip option.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="onboarding",
    group_name="onboarding_start",
    title="Onboarding Start (SSOT)",
    description=(
        "CANONICAL entry point for onboarding. Redirects to the appropriate "
        "step based on the user's gate state: no cookie → role-select, "
        "no storage → providers, no vault → vault-setup, else → complete."
    ),
    inputs=("semptify_uid?",),
    outputs=("redirect",),
    dependencies=("app.modules.onboarding.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="onboarding",
    group_name="onboarding_role_select",
    title="Onboarding Role Select (SSOT)",
    description=(
        "CANONICAL role selection page. The tenant picks their role "
        "(tenant, advocate, manager, admin, legal). Sets the role in the "
        "user cookie and proceeds to provider selection."
    ),
    inputs=("fresh?"),
    outputs=("page",),
    dependencies=("app.modules.onboarding.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="onboarding",
    group_name="onboarding_providers",
    title="Onboarding Provider Selection (SSOT)",
    description=(
        "CANONICAL storage provider selection page. The tenant chooses "
        "Google Drive, Dropbox, or OneDrive. Storage connection is "
        "MANDATORY — no skip option."
    ),
    inputs=("role?", "semptify_uid?"),
    outputs=("page",),
    dependencies=("app.modules.onboarding.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="onboarding",
    group_name="onboarding_oauth_start",
    title="Onboarding OAuth Start (SSOT)",
    description=(
        "CANONICAL initiate OAuth flow for a storage provider from onboarding. "
        "Redirects to the provider's auth page. Uses onboarding-specific "
        "callback URL to keep the flow separate from reconnect."
    ),
    inputs=("provider", "role"),
    outputs=("redirect",),
    dependencies=("app.modules.onboarding.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="onboarding",
    group_name="onboarding_oauth_callback",
    title="Onboarding OAuth Callback (SSOT)",
    description=(
        "CANONICAL OAuth callback handler for onboarding. Exchanges the auth "
        "code for tokens, stores them in the user's cloud, creates the user "
        "record, and redirects to vault setup."
    ),
    inputs=("provider", "code", "state"),
    outputs=("redirect", "user_id"),
    dependencies=("app.modules.onboarding.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="onboarding",
    group_name="onboarding_vault_setup_page",
    title="Onboarding Vault Setup Page (SSOT)",
    description=(
        "CANONICAL vault setup wizard page. Three-step UI: folders → "
        "security → inspect. Each step has its own API endpoint."
    ),
    inputs=("semptify_uid?",),
    outputs=("page",),
    dependencies=("app.modules.onboarding.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="onboarding",
    group_name="onboarding_vault_status",
    title="Onboarding Vault Status (SSOT)",
    description=(
        "CANONICAL vault status check during onboarding. Returns the current "
        "state of vault setup (folders_created, security_wired, verified). "
        "Used by the vault status poller."
    ),
    inputs=("user_id",),
    outputs=("folders_created", "security_wired", "verified"),
    dependencies=("app.modules.onboarding.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="onboarding",
    group_name="onboarding_vault_init",
    title="Onboarding Vault Init (SSOT)",
    description=(
        "CANONICAL vault initialization — Step 1: Create folders only. "
        "Creates .Semptify5.0/ root and all canonical subfolders in the "
        "user's cloud storage. Does NOT write files (Cloudflare 504 limit)."
    ),
    inputs=("user_id",),
    outputs=("ok", "folders"),
    dependencies=("app.modules.onboarding.router", "app.sdk.vault"),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="onboarding",
    group_name="onboarding_vault_security",
    title="Onboarding Vault Security (SSOT)",
    description=(
        "CANONICAL vault security wiring — Step 2: Write token backup and "
        "security files to the vault. Separate from folder creation to "
        "stay under Cloudflare's 30s gateway limit."
    ),
    inputs=("user_id",),
    outputs=("ok", "files_written"),
    dependencies=("app.modules.onboarding.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="onboarding",
    group_name="onboarding_vault_verify",
    title="Onboarding Vault Verify (SSOT)",
    description=(
        "CANONICAL vault verification — Step 3: Verify vault is fully "
        "operational. Checks folder accessibility and file integrity. "
        "Empty folders are valid (only failure is inaccessible/missing)."
    ),
    inputs=("user_id",),
    outputs=("ok", "verified_items"),
    dependencies=("app.modules.onboarding.router", "app.sdk.vault"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="onboarding",
    group_name="onboarding_system_check",
    title="Onboarding System Check (SSOT)",
    description=(
        "CANONICAL final system verification before onboarding completion. "
        "Runs health checks on storage, vault, and user record. "
        "Marks onboarding complete if all checks pass."
    ),
    inputs=("user_id",),
    outputs=("ok", "checks"),
    dependencies=("app.modules.onboarding.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="onboarding",
    group_name="onboarding_complete",
    title="Onboarding Complete (SSOT)",
    description=(
        "CANONICAL onboarding completion page. Marks the user as onboarded, "
        "sets the vault_initialized gate, and redirects to the tenant home."
    ),
    inputs=("semptify_uid?",),
    outputs=("redirect",),
    dependencies=("app.modules.onboarding.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="onboarding",
    group_name="onboarding_status_page",
    title="Onboarding Status Page (SSOT)",
    description=(
        "CANONICAL onboarding status page. Shows the user's current gate "
        "state and what steps remain. Used for debugging and resumption."
    ),
    inputs=("semptify_uid?",),
    outputs=("page", "gate_state"),
    dependencies=("app.modules.onboarding.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="onboarding",
    group_name="onboarding_ssot_navigation",
    title="Onboarding SSOT Navigation Export (SSOT)",
    description=(
        "CANONICAL export of navigation state for static files. Returns the "
        "navigation registry as a dict for client-side routing."
    ),
    inputs=(),
    outputs=("navigation",),
    dependencies=("app.modules.onboarding.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="onboarding",
    group_name="onboarding_reconnect",
    title="Onboarding Storage Reconnect (SSOT)",
    description=(
        "CANONICAL storage reconnect page. Shown when a user's storage token "
        "has expired or been revoked. Re-runs the OAuth flow without "
        "resetting the vault."
    ),
    inputs=("semptify_uid?",),
    outputs=("page",),
    dependencies=("app.modules.onboarding.reconnect",),
    deterministic=True,
))
