"""Intake module registration helper — FunctionGroupContracts.

The intake module is the ONE DOOR into the vault from the UI. All tenant
uploads flow through here. It accepts files, processes them, extracts
intelligence (dates, amounts, parties, issues), and routes them to the vault.
This is the RECORD pillar's entry point.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

# --- Upload Endpoints ---

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name="intake_upload",
        title="Intake Upload (SSOT)",
        description=(
            "CANONICAL single-file upload endpoint. Accepts a file, stores it, "
            "and queues it for processing. Returns the document ID and status. "
            "This is the primary upload endpoint for the tenant UI."
        ),
        inputs=("file", "user_id"),
        outputs=("doc_id", "filename", "status"),
        dependencies=("app.modules.intake.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name="intake_upload_auto",
        title="Intake Upload and Auto-Process (SSOT)",
        description=(
            "CANONICAL upload-and-process endpoint. Accepts a file, stores it, "
            "processes it immediately (classify, extract, detect issues), and "
            "returns the full result. This is the 'Add Record' button's backend."
        ),
        inputs=("file", "user_id"),
        outputs=("doc_id", "document_type", "issues_found", "dates", "amounts", "parties", "status"),
        dependencies=("app.modules.intake.router", "app.modules.documents.router"),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name="intake_upload_batch",
        title="Intake Batch Upload (SSOT)",
        description=(
            "CANONICAL batch upload endpoint. Accepts multiple files at once, "
            "stores and processes each, returns per-file results. "
            "Used when the tenant drops a folder of documents."
        ),
        inputs=("files", "user_id"),
        outputs=("results", "total", "succeeded", "failed"),
        dependencies=("app.modules.intake.router",),
        deterministic=False,
    )
)

# --- Processing ---

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name="intake_process_vault",
        title="Intake Process from Vault (SSOT)",
        description=(
            "CANONICAL process a document already in the vault. Re-runs the "
            "intake pipeline on an existing vault file. Used when a file was "
            "uploaded via sidebar but not yet processed."
        ),
        inputs=("doc_id", "user_id"),
        outputs=("doc_id", "document_type", "issues_found", "status"),
        dependencies=("app.modules.intake.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name="intake_process",
        title="Intake Process Document (SSOT)",
        description=(
            "CANONICAL processing of an uploaded document. Runs classification, "
            "extraction, and issue detection. Returns the processed document."
        ),
        inputs=("doc_id", "user_id"),
        outputs=("doc_id", "status", "document_type"),
        dependencies=("app.modules.intake.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name="intake_status",
        title="Intake Processing Status (SSOT)",
        description=(
            "CANONICAL status check for a processing document. Returns current "
            "status (queued, processing, completed, failed) and progress info."
        ),
        inputs=("doc_id",),
        outputs=("doc_id", "status", "progress"),
        dependencies=("app.modules.intake.router",),
        deterministic=True,
    )
)

# --- Retrieval ---

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name="intake_list_documents",
        title="Intake List Documents (SSOT)",
        description=(
            "CANONICAL list of intake documents for a user. Supports filtering by "
            "status. Returns document summaries with processing status."
        ),
        inputs=("user_id", "status?"),
        outputs=("documents",),
        dependencies=("app.modules.intake.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name="intake_get_document",
        title="Intake Get Document (SSOT)",
        description=(
            "CANONICAL retrieval of a specific intake document with all extraction "
            "results. Returns the full document record."
        ),
        inputs=("doc_id",),
        outputs=("document",),
        dependencies=("app.modules.intake.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name="intake_get_issues",
        title="Intake Document Issues (SSOT)",
        description=(
            "CANONICAL list of detected issues for a document. Returns issues "
            "with severity, description, and suggested actions."
        ),
        inputs=("doc_id",),
        outputs=("issues",),
        dependencies=("app.modules.intake.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name="intake_get_dates",
        title="Intake Document Dates (SSOT)",
        description=(
            "CANONICAL list of dates extracted from a document. Returns dates "
            "with context (what the date refers to) and confidence."
        ),
        inputs=("doc_id",),
        outputs=("dates",),
        dependencies=("app.modules.intake.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name="intake_get_amounts",
        title="Intake Document Amounts (SSOT)",
        description=(
            "CANONICAL list of monetary amounts extracted from a document. "
            "Returns amounts with context (fees, rent, deposits, charges)."
        ),
        inputs=("doc_id",),
        outputs=("amounts",),
        dependencies=("app.modules.intake.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name="intake_get_parties",
        title="Intake Document Parties (SSOT)",
        description=(
            "CANONICAL list of parties extracted from a document. Returns parties "
            "with role (landlord, tenant, witness, agency) and contact info."
        ),
        inputs=("doc_id",),
        outputs=("parties",),
        dependencies=("app.modules.intake.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name="intake_get_text",
        title="Intake Document Text (SSOT)",
        description=(
            "CANONICAL full extracted text for a document. Returns the text content extracted during processing."
        ),
        inputs=("doc_id",),
        outputs=("text",),
        dependencies=("app.modules.intake.router",),
        deterministic=True,
    )
)

# --- Analysis ---

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name="intake_critical_issues",
        title="Intake Critical Issues (SSOT)",
        description=(
            "CANONICAL list of all CRITICAL issues across all of a user's documents. "
            "Used by the tenant dashboard's critical alerts section."
        ),
        inputs=("user_id",),
        outputs=("issues", "total"),
        dependencies=("app.modules.intake.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name="intake_upcoming_deadlines",
        title="Intake Upcoming Deadlines (SSOT)",
        description=(
            "CANONICAL list of upcoming deadlines extracted from documents. "
            "Returns deadlines within the next N days (default 14). "
            "Used by the tenant dashboard's deadlines section."
        ),
        inputs=("user_id", "days?"),
        outputs=("deadlines", "total"),
        dependencies=("app.modules.intake.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name="intake_summary",
        title="Intake User Summary (SSOT)",
        description=(
            "CANONICAL summary of all intake documents for a user. Returns counts "
            "by status, total issues, critical issues, and upcoming deadlines. "
            "Used by the tenant dashboard."
        ),
        inputs=("user_id",),
        outputs=("total_documents", "by_status", "total_issues", "critical_issues", "upcoming_deadlines"),
        dependencies=("app.modules.intake.router",),
        deterministic=True,
    )
)

# --- Notarization & Verification ---

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name="intake_verify_notarization",
        title="Intake Verify Notarization (SSOT)",
        description=(
            "CANONICAL verification of a notarization ID. Returns whether the "
            "notarization is valid, the notary's info, and the document it covers."
        ),
        inputs=("notarization_id",),
        outputs=("valid", "notary", "document_id", "notarized_at"),
        dependencies=("app.modules.intake.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name="intake_chain_of_custody",
        title="Intake Chain of Custody (SSOT)",
        description=(
            "CANONICAL chain of custody retrieval for a notarized document. "
            "Returns the full custody chain from upload to notarization."
        ),
        inputs=("notarization_id",),
        outputs=("chain", "document_id"),
        dependencies=("app.modules.intake.router",),
        deterministic=True,
    )
)

# --- Enums (for frontend) ---

register_function_group(
    FunctionGroupContract(
        module="intake",
        group_name="intake_enums",
        title="Intake Enums (SSOT)",
        description=(
            "CANONICAL enumeration values for document types, intake statuses, "
            "issue severities, and supported languages. Used by the frontend to "
            "populate dropdowns and filters."
        ),
        inputs=(),
        outputs=("document_types", "intake_statuses", "issue_severities", "languages"),
        dependencies=("app.modules.intake.router",),
        deterministic=True,
    )
)
