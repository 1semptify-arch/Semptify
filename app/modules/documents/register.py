"""Documents module registration helper — FunctionGroupContracts.

The documents module is the RECORD pillar's intelligence layer. It sits on top
of the vault and provides document processing, classification, extraction, and
analysis. This is what makes a pile of files into an organized evidence record.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

# --- Document Processing ---

register_function_group(FunctionGroupContract(
    module="documents",
    group_name="documents_process",
    title="Documents Process (SSOT)",
    description=(
        "CANONICAL unified document processing. Takes a file from the vault, "
        "classifies it, extracts text/dates/amounts/parties, detects issues, "
        "and returns a unified response with all extracted intelligence. "
        "This is the main pipeline that turns a raw file into structured evidence."
    ),
    inputs=("file", "user_id"),
    outputs=("document_id", "document_type", "extracted_text", "dates", "amounts", "parties", "issues"),
    dependencies=("app.modules.documents.router", "app.modules.intake.router"),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="documents",
    group_name="documents_upload_simple",
    title="Documents Simple Upload (SSOT)",
    description=(
        "CANONICAL simple upload endpoint. Accepts a single file, stores it, "
        "processes it, and returns the document record. Lighter than the full "
        "unified process — used for quick captures."
    ),
    inputs=("file", "user_id"),
    outputs=("document_id", "filename", "document_type", "status"),
    dependencies=("app.modules.documents.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="documents",
    group_name="documents_list",
    title="Documents List (SSOT)",
    description=(
        "CANONICAL list of all processed documents for a user. Returns full "
        "document records with classification, extraction status, and metadata. "
        "Used by the tenant documents page."
    ),
    inputs=("user_id",),
    outputs=("documents",),
    dependencies=("app.modules.documents.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="documents",
    group_name="documents_get",
    title="Documents Get Detail (SSOT)",
    description=(
        "CANONICAL detailed view of a single document. Returns full metadata, "
        "extraction results, intelligence analysis, and processing status. "
        "Used by the document detail view."
    ),
    inputs=("doc_id", "user_id"),
    outputs=("document", "intelligence", "issues"),
    dependencies=("app.modules.documents.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="documents",
    group_name="documents_reprocess",
    title="Documents Reprocess (SSOT)",
    description=(
        "CANONICAL reprocessing of an existing document. Re-runs classification "
        "and extraction on an already-stored file. Used when extraction models "
        "improve or a document was partially processed."
    ),
    inputs=("doc_id", "user_id"),
    outputs=("document_id", "status", "document_type"),
    dependencies=("app.modules.documents.router",),
    deterministic=False,
))

# --- Intelligence & Analysis ---

register_function_group(FunctionGroupContract(
    module="documents",
    group_name="documents_intelligence",
    title="Documents Intelligence Analysis (SSOT)",
    description=(
        "CANONICAL intelligence analysis for a document. Returns extracted "
        "dates, amounts, parties, issues, deadlines, and suggested actions. "
        "Used by the document detail view's intelligence panel."
    ),
    inputs=("doc_id", "user_id"),
    outputs=("dates", "amounts", "parties", "issues", "deadlines", "suggested_actions"),
    dependencies=("app.modules.documents.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="documents",
    group_name="documents_urgent",
    title="Documents Urgent List (SSOT)",
    description=(
        "CANONICAL list of urgent documents requiring attention. Based on "
        "issue severity, upcoming deadlines, and document type. "
        "Used by the tenant dashboard's urgent section."
    ),
    inputs=("user_id",),
    outputs=("documents",),
    dependencies=("app.modules.documents.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="documents",
    group_name="documents_text",
    title="Documents Extracted Text (SSOT)",
    description=(
        "CANONICAL retrieval of the full extracted text for a document. "
        "Returns the text content extracted during processing. "
        "Used for document viewing and search."
    ),
    inputs=("doc_id", "user_id"),
    outputs=("text", "language"),
    dependencies=("app.modules.documents.router",),
    deterministic=True,
))

# --- Classification & Training ---

register_function_group(FunctionGroupContract(
    module="documents",
    group_name="documents_update_category",
    title="Documents Update Category (SSOT)",
    description=(
        "CANONICAL update of a document's category. Tenant can correct the "
        "auto-classification. The correction feeds back into training stats."
    ),
    inputs=("doc_id", "user_id", "category"),
    outputs=("doc_id", "category"),
    dependencies=("app.modules.documents.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="documents",
    group_name="documents_train_correct",
    title="Documents Train Correct (SSOT)",
    description=(
        "CANONICAL submit a classification correction for training. The tenant "
        "confirms or corrects the auto-classification, which improves future "
        "classification for all users."
    ),
    inputs=("doc_id", "user_id", "corrected_type"),
    outputs=("status",),
    dependencies=("app.modules.documents.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="documents",
    group_name="documents_train_stats",
    title="Documents Training Stats (SSOT)",
    description=(
        "CANONICAL training statistics. Returns counts of confirmed vs corrected "
        "classifications, learned patterns, and model accuracy metrics. "
        "Admin-only view for model improvement tracking."
    ),
    inputs=(),
    outputs=("total_documents", "confirmed", "corrected", "accuracy", "patterns"),
    dependencies=("app.modules.documents.router",),
    deterministic=True,
))

# --- View & Export ---

register_function_group(FunctionGroupContract(
    module="documents",
    group_name="documents_view",
    title="Documents View (SSOT)",
    description=(
        "CANONICAL in-browser view of a document. Returns a viewable "
        "representation (HTML/PDF/image) for the tenant document viewer."
    ),
    inputs=("doc_id", "user_id"),
    outputs=("content", "content_type"),
    dependencies=("app.modules.documents.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="documents",
    group_name="documents_thumbnail",
    title="Documents Thumbnail (SSOT)",
    description=(
        "CANONICAL thumbnail image for a document. Used in document grids, "
        "sidebar lists, and timeline entries for visual identification."
    ),
    inputs=("doc_id", "user_id"),
    outputs=("thumbnail", "content_type"),
    dependencies=("app.modules.documents.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="documents",
    group_name="documents_export",
    title="Documents Export (SSOT)",
    description=(
        "CANONICAL export of all documents as a downloadable archive. "
        "GDPR-compliant data export. Includes all files, metadata, and "
        "certificates in a zip."
    ),
    inputs=("user_id",),
    outputs=("file_stream", "filename"),
    dependencies=("app.modules.documents.router",),
    deterministic=True,
))

# --- Timeline & Summary Integration ---

register_function_group(FunctionGroupContract(
    module="documents",
    group_name="documents_timeline",
    title="Documents Timeline (SSOT)",
    description=(
        "CANONICAL timeline of document events for a user. Returns events "
        "sorted by date — uploads, processing, classification corrections, "
        "and detected issues. Used by the tenant timeline page."
    ),
    inputs=("user_id",),
    outputs=("events",),
    dependencies=("app.modules.documents.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="documents",
    group_name="documents_summary",
    title="Documents Summary (SSOT)",
    description=(
        "CANONICAL summary of a user's document portfolio. Returns counts by "
        "type, total size, urgent count, and recent activity. "
        "Used by the tenant dashboard."
    ),
    inputs=("user_id",),
    outputs=("total_documents", "by_type", "urgent_count", "recent_activity"),
    dependencies=("app.modules.documents.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="documents",
    group_name="documents_auto_timeline",
    title="Documents Auto-Timeline (SSOT)",
    description=(
        "CANONICAL auto-populate timeline from a document's extracted dates. "
        "Takes dates found in the document and creates timeline events for "
        "each. Saves the tenant from manually entering dates."
    ),
    inputs=("doc_id", "user_id"),
    outputs=("created_events", "total_created"),
    dependencies=("app.modules.documents.router", "app.modules.timeline.router"),
    deterministic=False,
))
