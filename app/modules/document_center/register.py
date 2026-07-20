"""Document Center module contracts — SSOT for DC API signatures.

Read these before calling any DC endpoint. If a method or field is not here,
it does not exist. Do not invent signatures.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="document_center",
        group_name="dc_list",
        title="Document Center List (SSOT)",
        description=(
            "CANONICAL document list for the DC left panel. Returns all vault documents "
            "for the authenticated user, each with: id, filename, uploaded_at, "
            "document_type, overlay_count (null — real count requires per-doc cloud fetch), "
            "verification_status ('new'|'review'|'verified'). "
            "Call dc_overlays for the authoritative count per document."
        ),
        inputs=("user_id",),
        outputs=("documents", "total", "generated_at"),
        dependencies=("app.modules.document_center.router", "app.services.vault_upload_service"),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="document_center",
        group_name="dc_unlocks",
        title="Document Center Unlocks (SSOT)",
        description=(
            "CANONICAL unlock state computation for DC feature modules. "
            "Iterates all VaultDocuments for a user, synthesizes overlay scores in memory (no cloud I/O), "
            "and checks four thresholds: Timeline (1 doc Dates+Parties>=80%), "
            "Journal (2+ docs overall>=60%), Contact Manager (Parties==100%), "
            "Case Builder (3+ docs overall>=80%). "
            "Returns unlocks list with name/icon/threshold/unlocked/progress per item."
        ),
        inputs=("user_id",),
        outputs=("unlocks", "doc_count", "generated_at"),
        dependencies=("app.modules.document_center.router", "app.services.vault_upload_service"),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="document_center",
        group_name="dc_overlays",
        title="Document Center Overlays (SSOT)",
        description=(
            "CANONICAL overlay progress data for the DC right panel. "
            "Reads REAL overlays from UnifiedOverlayManager.get_overlays() in the user's "
            "cloud storage, keyed by document_id = doc.safe_filename. "
            "Maps real overlay payloads to 6 progress items: Certified Upload, Document Type, "
            "Text Extraction, Dates, Parties, Amounts. "
            "NO DB FALLBACK. If no real overlays exist or cloud is unavailable, returns "
            "an honest status message derived from DocumentPipelineIndex.deep_ocr_status "
            "(pending/processing/complete/failed/needs_reprocess) with overlay_source='pipeline'. "
            "Returns has_data, overall_pct, overlays, overlay_count, overlay_source "
            "('real'|'pipeline'), status, message, detail."
        ),
        inputs=("vault_id", "user_id"),
        outputs=("has_data", "overall_pct", "overlays", "overlay_count", "overlay_source", "status"),
        dependencies=(
            "app.modules.document_center.router",
            "app.services.vault_upload_service",
            "app.services.unified_overlay_manager",
            "app.core.oauth_token_manager",
        ),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="document_center",
        group_name="dc_view",
        title="Document Center View (SSOT)",
        description=(
            "CANONICAL inline document stream for the DC viewer iframe. "
            "Authenticates via session cookie (same-origin iframe). "
            "Fetches file bytes from vault storage and returns them with "
            "Content-Disposition: inline so the browser renders PDF/image natively. "
            "Returns 503 if the user's OAuth token is missing (needs reconnect)."
        ),
        inputs=("vault_id", "user_id"),
        outputs=("file_bytes", "mime_type", "filename"),
        dependencies=(
            "app.modules.document_center.router",
            "app.services.vault_upload_service",
            "app.core.oauth_token_manager",
        ),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="document_center",
        group_name="dc_set_type",
        title="Document Center Set Document Type (SSOT)",
        description=(
            "CANONICAL document type setter for the DC viewer dropdown. "
            "Called when the tenant identifies or corrects a document's type. "
            "Validates against the allowed set: lease, notice_to_vacate, repair_request, "
            "rent_receipt, move_in_inspection, court_summons, correspondence, other. "
            "Persistence (vault update + overlay creation) is wired in Slice 4."
        ),
        inputs=("doc_id", "document_type", "user_id"),
        outputs=("ok", "doc_id", "document_type", "note"),
        dependencies=("app.modules.document_center.router",),
        deterministic=False,
    )
)
