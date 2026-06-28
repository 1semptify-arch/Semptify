"""Document Center module contracts — SSOT for DC API signatures.

Read these before calling any DC endpoint. If a method or field is not here,
it does not exist. Do not invent signatures.
"""
from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="document_center",
    group_name="dc_list",
    title="Document Center List (SSOT)",
    description=(
        "CANONICAL document list for the DC left panel. Returns all vault documents "
        "for the authenticated user, each with: id, filename, uploaded_at, "
        "document_type, overlay_count, verification_status. "
        "overlay_count and verification_status are 0/'new' until Slice 4 wires "
        "the UnifiedOverlayManager bridge."
    ),
    inputs=("user_id",),
    outputs=("documents", "total", "generated_at"),
    dependencies=("app.modules.document_center.router", "app.services.vault_upload_service"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="document_center",
    group_name="dc_overlays",
    title="Document Center Overlays (SSOT)",
    description=(
        "CANONICAL overlay progress data for the DC right panel. "
        "Synthesizes 6 overlay progress items from VaultDocument metadata already in the DB: "
        "Certified Upload, Document Type, Text Extraction, Dates, Parties, Amounts. "
        "No cloud storage I/O required — always fast. "
        "Returns has_data, overall_pct, and overlays list with pct/icon/goal per item."
    ),
    inputs=("vault_id", "user_id"),
    outputs=("has_data", "overall_pct", "overlays"),
    dependencies=("app.modules.document_center.router", "app.services.vault_upload_service"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
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
    dependencies=("app.modules.document_center.router", "app.services.vault_upload_service",
                  "app.core.oauth_token_manager"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
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
))
