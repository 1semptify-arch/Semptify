"""Case Review module contracts — SSOT for the evidence-index API.

Read these before calling any endpoint. If a method or field is not here,
it does not exist. Do not invent signatures.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="case_review",
        group_name="cr_status",
        title="Case Review Status (SSOT)",
        description=(
            "CANONICAL unlock check. Returns {unlocked} — true when the tenant has marked "
            "legal_share_initialized (share_marker overlay in their vault) or holds the "
            "module capability. Ungated: a locked tenant needs this to render the lock state."
        ),
        inputs=("user_id",),
        outputs=("unlocked",),
        dependencies=("app.modules.case_review.router", "app.modules.case_review.service"),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_review",
        group_name="cr_share_initialized",
        title="Case Review Share Initialized (SSOT)",
        description=(
            "CANONICAL flag setter. Tenant self-marks legal_share_initialized — declaring they "
            "have shared their case file with an attorney/legal reviewer (the share itself happens "
            "outside Semptify in the tenant's own storage provider). Writes a share_marker "
            "EVIDENCE_INDEX overlay (durable record, per case or global) and grants the "
            "app.modules.case_review.router capability with source=legal_share_initialized. "
            "Idempotent per anchor. Optional case_id validates the case exists first."
        ),
        inputs=("user_id", "case_id"),
        outputs=("unlocked", "marker_id"),
        dependencies=(
            "app.modules.case_review.router",
            "app.modules.case_review.service",
            "app.core.capabilities",
        ),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_review",
        group_name="cr_cases",
        title="Case Review Case List (SSOT)",
        description=(
            "CANONICAL case picker. Lists the tenant's INCIDENT overlay records (same source as "
            "Case Builder) — incident_id, title, status, incident_type, updated_at. Locked until "
            "legal_share_initialized."
        ),
        inputs=("user_id",),
        outputs=("cases",),
        dependencies=("app.modules.case_review.router", "app.services.incident_store"),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_review",
        group_name="cr_documents",
        title="Case Review Documents (SSOT)",
        description=(
            "CANONICAL per-case document list. Returns every vault document merged with its case "
            "tag: {id, vault_id, name, document_type, uploaded_at, vault_path, category, "
            "evidence_type, tagged}. Untagged docs form the add-to-index pool — tagging is metadata "
            "only and never moves the tenant's actual cloud files."
        ),
        inputs=("user_id", "case_id"),
        outputs=("case_id", "documents"),
        dependencies=(
            "app.modules.case_review.router",
            "app.modules.case_review.service",
            "app.services.vault_upload_service",
        ),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_review",
        group_name="cr_tag",
        title="Case Review Document Tag (SSOT)",
        description=(
            "CANONICAL tag setter/remover. category in {foundational, discovery, motion, evidence, "
            "misc}; evidence_type in {none, documentary, digital, physical, witness}. Upserts a "
            "doc_tag EVIDENCE_INDEX overlay; DELETE removes it. Both are overlay writes only — "
            "the original document is never touched."
        ),
        inputs=("user_id", "case_id", "document_id", "category", "evidence_type"),
        outputs=("document_id", "category", "evidence_type", "removed"),
        dependencies=("app.modules.case_review.router", "app.modules.case_review.service"),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_review",
        group_name="cr_legend",
        title="Case Review Legend (SSOT)",
        description=(
            "CANONICAL color legend — one legend overlay per case, entries [{label, color}], "
            "editable by the user. Color is purely visual (highlight ↔ footnote matching) and "
            "carries no semantic meaning. Unset cases get the starter set (Key fact / Date or "
            "deadline / Disputed / Money amount)."
        ),
        inputs=("user_id", "case_id", "entries"),
        outputs=("case_id", "entries"),
        dependencies=("app.modules.case_review.router", "app.modules.case_review.service"),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_review",
        group_name="cr_notes",
        title="Case Review Evidence Notes (SSOT)",
        description=(
            "CANONICAL evidence-note CRUD. A note is free text plus links[] — "
            "[{document_id, vault_path?, name?, location?}] — so one entry can point at several "
            "places across several documents (multi-document linking, spec §4). certified is "
            "hardcoded False in the payload — nothing this module produces is ever certified."
        ),
        inputs=("user_id", "case_id", "note_id", "text", "links", "legend_label"),
        outputs=("notes", "note", "deleted"),
        dependencies=("app.modules.case_review.router", "app.modules.case_review.service"),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_review",
        group_name="cr_export",
        title="Case Review Export (SSOT)",
        description=(
            "CANONICAL paste-ready plain-text evidence index (text/plain): case title, legend, "
            "documents grouped by category, then numbered notes with their document/location "
            "links. Labeled 'working notes, not certified records'. This is the attorney-meeting "
            "artifact — copy/paste, not filing."
        ),
        inputs=("user_id", "case_id"),
        outputs=("text",),
        dependencies=(
            "app.modules.case_review.router",
            "app.modules.case_review.service",
            "app.services.vault_upload_service",
        ),
        deterministic=True,
    )
)
