"""
Privacy & Acceptable-Use SSOT
==============================

Single source of truth for:

1. **Role-scoped storage rules** — what each role may store on Semptify
   servers, what must live only in the user's own cloud vault, and what
   must never be collected at all. Extends the canonical Role-Scoped Data
   Privacy Policy in ``SECURITY_AND_PRIVACY_ARCHITECTURE.md`` (§"Role-Scoped
   Data Privacy Policy") into an importable, enforceable structure.

2. **Canonical disclaimer registry** — every disclaimer a module or role
   surface may display, keyed by stable ID. Modules MUST reference these
   IDs (or import the strings) rather than defining their own
   ``LEGAL_DISCLAIMER``-style constants. Drift here is a known failure
   pattern — three divergent variants already existed across
   ``law_library``, ``eviction_defense``, and ``role_ui`` before this
   registry.

3. **Acceptable-use boundaries** — the canonical lists of what Semptify
   will and will not do (service-side) and what users may and may not do
   with the platform (user-side).

Companion human-readable policy: ``docs/admin/PRIVACY_AND_ACCEPTABLE_USE_SSOT.md``.
UPL risk tiers and banned phrases stay in ``app/core/upl_guardrails.py`` —
this module imports, never redefines, those strings.

Rules for editing:
- Disclaimer text changes happen HERE, not in copies elsewhere.
- New module? Assign it a pillar + explicit disclaimer list in
  ``MODULE_DISCLAIMERS``. ``"*"`` is a floor, not a substitute.
- New role? Add a ``RoleStorageRule`` entry AND a row in the companion doc.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.upl_guardrails import UPL_DISCLAIMER, UPL_DISCLAIMER_LONG

# ---------------------------------------------------------------------------
# 1. Role-scoped storage rules
# ---------------------------------------------------------------------------
#
# Four buckets per role:
#   server_allowed   — fields Semptify's database MAY hold for this role
#   vault_only       — data that may exist ONLY in the user's own cloud vault
#   vault_forbidden  — things no module may ever write into a user's vault
#   never_collected  — data that must not exist anywhere in the system
#
# "The user's vault" means the cloud storage account the USER controls
# (Google Drive / Dropbox / OneDrive). For a tenant, the vault is theirs.
# For staff roles, tenant data never enters the staff member's own vault —
# shared records live in the TENANT's vault under consent.


@dataclass(frozen=True)
class RoleStorageRule:
    """Storage boundary for one role. Frozen — never mutate at runtime."""

    server_allowed: tuple[str, ...] = ()
    vault_only: tuple[str, ...] = ()
    vault_forbidden: tuple[str, ...] = ()
    never_collected: tuple[str, ...] = ()


_PLATFORM_NEVER_COLLECTED: tuple[str, ...] = (
    "activity_logs",
    "click_tracking",
    "page_view_history",
    "ip_address_logs",  # transient rate-limit use only, never persisted
    "device_fingerprints",
    "location_tracking",
    "usage_analytics",
    "behavioral_profiles",
    "advertising_identifiers",
)

_TENANT_PII: tuple[str, ...] = (
    "full_name",
    "email_address",
    "home_or_rental_address",
    "phone_number",
    "date_of_birth",
    "case_details",  # eviction reason, rent amount, hearing dates
    "document_content",
    "timeline_entries",
    "journal_entries",
    "evidence_files",
    "retaliation_events",
    "consent_records",
)

_VAULT_FORBIDDEN_ALL: tuple[str, ...] = (
    "other_users_data",
    "server_secrets_or_keys",
    "server_logs",
    "executable_code",
    "tracking_beacons",
    "data_scoped_to_other_roles",
)

ROLE_STORAGE_RULES: dict[str, RoleStorageRule] = {
    "tenant": RoleStorageRule(
        # Zero-PII-on-server hard rule. Per SECURITY_AND_PRIVACY_ARCHITECTURE.md
        # §"Role-Scoped Data Privacy Policy": no exceptions without explicit
        # informed consent through a consent gate.
        server_allowed=(
            "anonymous_user_id",  # hashed provider+subject — contains no PII
            "storage_provider_name",  # google_drive | dropbox | onedrive
            "provider_subject_id",  # opaque OAuth subject string
            "onboarding_gate_flags",  # completed_groups
            "role_preference",  # default_role
            "timestamps",  # created_at, last_login
            "jurisdiction_state_code",  # derived, not PII under GDPR/CCPA
            "encrypted_oauth_tokens",  # AES-256-GCM, session-scoped
            "tenant_created_landlord_contacts",  # explicit tenant records only
        ),
        vault_only=_TENANT_PII + (
            "case_packets",
            "court_form_drafts",
            "notes_and_sticky_notes",
            "contacts",  # tenant's own contact book
            "correspondence_records",
            "retaliation_assessment_notes",
        ),
        vault_forbidden=_VAULT_FORBIDDEN_ALL + (
            "scraped_opinion_text",  # raw scrapes never mixed into user records
            "ai_training_data",
            "other_tenants_case_data",
        ),
        never_collected=_PLATFORM_NEVER_COLLECTED,
    ),
    "manager": RoleStorageRule(
        # Manager = tenant-rights advocate with a multi-client caseload
        # (.devin/rules/04-roles-and-identity.md), NOT a property manager.
        server_allowed=(
            "anonymous_user_id",
            "storage_provider_name",
            "provider_subject_id",
            "operational_case_metadata",  # caseload state, task lists — own work
            "relationship_records",  # advocacy links to clients
            "timestamps",
        ),
        vault_only=(
            "own_notes_and_drafts",
            "client_consented_shared_records",
        ),
        vault_forbidden=_VAULT_FORBIDDEN_ALL + (
            "client_pii_without_documented_consent",
            "other_clients_case_data",
        ),
        never_collected=_PLATFORM_NEVER_COLLECTED + (
            "tenant_pii_without_consent",
        ),
    ),
    "advocate": RoleStorageRule(
        # Case coordination data only; individual advocate data policy still
        # pending — until defined, treat like manager (consent-gated).
        server_allowed=(
            "anonymous_user_id",
            "storage_provider_name",
            "provider_subject_id",
            "case_coordination_metadata",
            "relationship_records",
            "timestamps",
        ),
        vault_only=(
            "own_notes_and_drafts",
            "client_consented_shared_records",
        ),
        vault_forbidden=_VAULT_FORBIDDEN_ALL + (
            "client_pii_without_documented_consent",
        ),
        never_collected=_PLATFORM_NEVER_COLLECTED + (
            "tenant_pii_without_consent",
        ),
    ),
    "legal": RoleStorageRule(
        # Sub-roles: attorney, judge, clerk, paralegal — all require
        # bar_license_number. Legal has READ-ONLY tenant vault access
        # (04-roles-and-identity.md): no vault_write, ever.
        server_allowed=(
            "anonymous_user_id",
            "storage_provider_name",
            "provider_subject_id",
            "legal_sub_role",
            "bar_license_hash",  # public credential, stored hashed
            "relationship_records",  # engagement links
            "timestamps",
        ),
        vault_only=(
            "work_product_drafts",  # in legal's own vault
            "legal_overlays",  # created via overlay_create_legal
        ),
        vault_forbidden=_VAULT_FORBIDDEN_ALL + (
            "writes_to_tenant_vault",  # read-only access — hard rule
            "client_files_in_own_vault_without_engagement",
        ),
        never_collected=_PLATFORM_NEVER_COLLECTED + (
            "privileged_content_without_engagement_record",
        ),
    ),
    "admin": RoleStorageRule(
        server_allowed=(
            "anonymous_user_id",
            "role_flags",
            "anonymized_audit_events",
            "timestamps",
        ),
        vault_only=(
            "own_admin_notes",
        ),
        vault_forbidden=_VAULT_FORBIDDEN_ALL,
        never_collected=_PLATFORM_NEVER_COLLECTED + (
            "tenant_pii",
            "user_document_content",
        ),
    ),
    "research": RoleStorageRule(
        server_allowed=(
            "aggregated_anonymized_data",
        ),
        vault_only=(),
        vault_forbidden=_VAULT_FORBIDDEN_ALL,
        never_collected=_PLATFORM_NEVER_COLLECTED + (
            "individual_level_data",
            "tenant_pii",
        ),
    ),
}

# Legal sub-roles inherit the "legal" rule. Convenience lookup.
_LEGAL_SUB_ROLES: tuple[str, ...] = ("attorney", "judge", "clerk", "paralegal")


def storage_rule_for(role: str, legal_sub_role: str | None = None) -> RoleStorageRule:
    """Return the RoleStorageRule for a role (legal sub-roles map to 'legal').

    Unknown roles return the most restrictive rule (research) — fail closed.
    """
    if legal_sub_role in _LEGAL_SUB_ROLES:
        return ROLE_STORAGE_RULES["legal"]
    return ROLE_STORAGE_RULES.get(role, ROLE_STORAGE_RULES["research"])


def may_store_on_server(role: str, field_name: str, *, legal_sub_role: str | None = None) -> bool:
    """True only if `field_name` is explicitly in the role's server_allowed list.

    Fail-closed: anything not listed is treated as vault-only. This is the
    enforcement helper for the consent-gate rule — a module wanting a field
    not in server_allowed must implement the consent gate first.
    """
    return field_name in storage_rule_for(role, legal_sub_role).server_allowed


# ---------------------------------------------------------------------------
# 2. Canonical disclaimer registry
# ---------------------------------------------------------------------------
#
# Every disclaimer a module or role surface may show, keyed by stable ID.
# Modules reference these IDs (or import the values). NEVER define a local
# DISCLAIMER constant — that is how the three divergent LEGAL_DISCLAIMER
# variants happened.

DISCLAIMERS: dict[str, str] = {
    # UPL — canonical text lives in upl_guardrails.py; aliased here so this
    # registry is the single lookup point.
    "not_legal_advice": UPL_DISCLAIMER,
    "not_legal_advice_long": UPL_DISCLAIMER_LONG,
    # Educational-information disclaimer — merges the three former
    # LEGAL_DISCLAIMER variants into one canonical text.
    "educational_info": (
        "This information is for education only and is not legal advice. "
        "Laws change — verify current statutes with official sources. For "
        "advice about your situation, talk to a licensed attorney or your "
        "local legal aid organization."
    ),
    # Tenant data promise — shown on surfaces that handle tenant records.
    "tenant_zero_pii": (
        "Your documents and personal details stay in your own cloud storage. "
        "Semptify does not keep copies on its servers."
    ),
    # Consent gate — shown BEFORE any module stores tenant data server-side.
    "consent_gate": (
        "This feature stores the listed information on Semptify's servers. "
        "It is optional — everything else still works if you skip it. You "
        "can withdraw consent and delete the stored data at any time."
    ),
    # AI-generated output.
    "ai_generated": (
        "Generated by AI — may contain errors. Verify important details "
        "against the original documents or official sources."
    ),
    # Third-party / public-record content (reviews, scraped public pages).
    "public_content_opinion": (
        "This content comes from public sources and reflects other people's "
        "opinions and reports. Semptify does not verify or endorse it."
    ),
    # External resources (legal aid, hotlines, agencies).
    "external_resource": (
        "Semptify does not run these organizations. Availability, hours, and "
        "services can change — confirm directly with them."
    ),
    # Ephemeral document processing (OCR, text extraction, recognition).
    "ephemeral_processing": (
        "Documents are processed in memory to help organize them and are not "
        "stored on Semptify's servers."
    ),
    # Shared-access notice — shown when an advocate/manager/legal role can
    # see tenant records under a relationship.
    "shared_access": (
        "Records you share are visible to the person you shared them with. "
        "You can revoke sharing at any time."
    ),
    # Emergency redirect — Semptify is not an emergency service.
    "emergency_redirect": (
        "Semptify is not an emergency service. If you are in danger or facing "
        "an immediate lockout or shutoff, call 911 or 211 now."
    ),
}


def disclaimer(disclaimer_id: str) -> str:
    """Return canonical disclaimer text by ID. Raises KeyError on unknown ID —
    unknown IDs are a bug, not a content gap; register the text above first."""
    return DISCLAIMERS[disclaimer_id]


# ---------------------------------------------------------------------------
# 3. Module and role disclaimer requirements
# ---------------------------------------------------------------------------
#
# Every module maps to required disclaimer IDs. "*" is the platform floor —
# applied to every module IN ADDITION TO its own list, never instead of it.
# A module not listed here must be added before it ships user-facing output.

MODULE_DISCLAIMERS: dict[str, tuple[str, ...]] = {
    # Floor for everything.
    "*": ("not_legal_advice",),
    # KNOW pillar — legal information surfaces.
    "law_library": ("educational_info", "external_resource"),
    "state_laws": ("educational_info",),
    "legal_intel": ("educational_info",),
    "litigation_intelligence": ("educational_info",),
    "legal_trails": ("educational_info",),
    "research": ("educational_info",),
    "housing_accountability": ("public_content_opinion", "educational_info"),
    "accountability_ledger": ("public_content_opinion",),
    "resource_directory": ("external_resource",),
    "search": ("educational_info",),
    "free_api": ("external_resource",),
    # ACT pillar — guided action / form generation.
    "eviction_defense": ("educational_info", "not_legal_advice_long"),
    "case_builder": ("educational_info",),
    "court_forms": ("educational_info", "not_legal_advice_long"),
    "court_packet": ("educational_info", "not_legal_advice_long"),
    "legal_filing": ("educational_info", "not_legal_advice_long"),
    "court_forms_prep": ("educational_info",),
    "zoom_court": ("educational_info",),
    "zoom_court_prep": ("educational_info",),
    "complaints": ("educational_info", "external_resource"),
    "tactics": ("educational_info",),
    "plan_maker": ("educational_info",),
    "guided_intake": ("educational_info",),
    "mndes": ("educational_info", "external_resource"),
    "dakota_defense": ("educational_info",),
    "counterclaim": ("educational_info",),
    "campaign": ("educational_info", "public_content_opinion"),
    "public_exposure": ("public_content_opinion", "educational_info"),
    # RECORD pillar — tenant data surfaces.
    "document_center": ("tenant_zero_pii", "ephemeral_processing"),
    "vault": ("tenant_zero_pii",),
    "documents": ("tenant_zero_pii", "ephemeral_processing"),
    "document_intake": ("tenant_zero_pii", "ephemeral_processing"),
    "document_converter": ("ephemeral_processing",),
    "pdf_tools": ("ephemeral_processing",),
    "recognition": ("ai_generated", "ephemeral_processing"),
    "extraction": ("ai_generated", "ephemeral_processing"),
    "journal": ("tenant_zero_pii",),
    "timeline": ("tenant_zero_pii",),
    "calendar": ("tenant_zero_pii",),
    "contacts": ("tenant_zero_pii", "shared_access"),
    "correspondence": ("tenant_zero_pii",),
    "rent": ("tenant_zero_pii",),
    "dispute_tracker": ("tenant_zero_pii", "educational_info"),
    "sticky_notes": ("tenant_zero_pii",),
    "briefcase": ("tenant_zero_pii",),
    # AI surfaces.
    "brain": ("ai_generated", "educational_info"),
    "local_ai": ("ai_generated",),
    "judge": ("ai_generated", "educational_info"),
    # Sharing / multi-role surfaces.
    "advocate": ("shared_access", "educational_info"),
    "manager": ("shared_access",),
    "document_delivery": ("shared_access",),
    "document_sharing": ("shared_access",),
    # Consent-gated storage.
    "cloud_sync": ("consent_gate", "tenant_zero_pii"),
    "analytics": ("consent_gate",),
    "info_donation": ("consent_gate",),
    # Scraped / public-data pipelines.
    "crawler": ("public_content_opinion",),
    "fraud_exposure": ("public_content_opinion", "educational_info"),
    # Safety surfaces.
    "safety": ("emergency_redirect", "external_resource"),
    "user_concerns": ("emergency_redirect",),
    # GOVERN pillar — admin/dev surfaces, not tenant-facing.
    "admin_console": (),
    "admin_api": (),
    "admin_auth": (),
    "run_modules": (),
    "system_health": (),
    "debug": (),
    "dev_lab": (),
    "development": (),
    "role_ui": ("educational_info",),  # renders legal info in role previews
    "onboarding": ("tenant_zero_pii", "not_legal_advice_long"),
}

# Disclaimers required on role-level surfaces (role home pages, role tools).
ROLE_DISCLAIMERS: dict[str, tuple[str, ...]] = {
    "tenant": ("tenant_zero_pii", "not_legal_advice"),
    "manager": ("shared_access", "not_legal_advice"),
    "advocate": ("shared_access", "not_legal_advice"),
    "legal": ("shared_access", "not_legal_advice_long"),
    "admin": (),
    "research": (),
}


def disclaimers_for_module(module_name: str) -> tuple[str, ...]:
    """All required disclaimer IDs for a module: its own list + the floor.

    Unknown modules get the floor only — but per the rule above, an unlisted
    module must not ship user-facing output until it is added to
    ``MODULE_DISCLAIMERS``.
    """
    return tuple(dict.fromkeys(MODULE_DISCLAIMERS.get(module_name, ()) + MODULE_DISCLAIMERS["*"]))


def disclaimers_for_role(role: str, legal_sub_role: str | None = None) -> tuple[str, ...]:
    """Required disclaimer IDs for a role surface. Legal sub-roles map to 'legal'."""
    if legal_sub_role in _LEGAL_SUB_ROLES:
        return ROLE_DISCLAIMERS["legal"]
    return ROLE_DISCLAIMERS.get(role, ("not_legal_advice",))


# ---------------------------------------------------------------------------
# 4. Acceptable use — what Semptify will and will not do
# ---------------------------------------------------------------------------
#
# Two directions:
#   service_* — commitments the platform makes (the "will / will not" list)
#   user_*    — rules for using the platform (acceptable-use policy)

ACCEPTABLE_USE: dict[str, tuple[str, ...]] = {
    "service_will": (
        "organize_user_documents",  # store, index, timeline the user's own records
        "show_verified_facts",  # statutes, court rules, public records with sources
        "explain_legal_concepts",  # plain-language education, never advice
        "track_deadlines",  # compute and surface dates from the user's own events
        "connect_to_help",  # legal aid, hotlines, agencies — real outside paths
        "generate_organizational_documents",  # packets, timelines, indices of user facts
        "keep_tenant_data_in_user_vault",  # zero tenant PII on servers
        "let_users_delete_everything",  # full data control stays with the user
    ),
    "service_will_not": (
        "give_legal_advice",  # UPL — see upl_guardrails.py VERY_HIGH_DO_NOT_BUILD
        "predict_case_outcomes",
        "represent_users",  # no attorney-client relationship, ever
        "file_documents_without_attorney_review",
        "contact_landlords_or_agencies_on_user_behalf",
        "store_tenant_pii_without_consent",
        "sell_or_share_user_data",
        "run_ads_or_tracking",
        "create_accounts_or_require_registration",
        "act_from_fear_resentment_dishonesty_greed",  # standing motivation rule
        "use_urgency_tactics_or_dark_patterns",
    ),
    "user_may": (
        "organize_own_records",
        "share_own_records_with_helpers",  # advocates, attorneys — revocable
        "export_own_data_anytime",
        "use_for_any_lawful_housing_purpose",
    ),
    "user_may_not": (
        "upload_other_peoples_private_data_without_right",  # no third-party PII dumps
        "use_for_harassment_or_doxxing",  # no dossiers on private individuals
        "misrepresent_semtify_output_as_legal_advice",
        "probe_or_attack_the_service",  # no security testing against production
        "scrape_private_individuals",  # companies only, per pmas_foundation rules
    ),
}


__all__ = [
    "RoleStorageRule",
    "ROLE_STORAGE_RULES",
    "storage_rule_for",
    "may_store_on_server",
    "DISCLAIMERS",
    "disclaimer",
    "MODULE_DISCLAIMERS",
    "ROLE_DISCLAIMERS",
    "disclaimers_for_module",
    "disclaimers_for_role",
    "ACCEPTABLE_USE",
]
