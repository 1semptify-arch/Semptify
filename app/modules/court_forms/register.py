"""Court Forms module registration helper — FunctionGroupContracts.

The court forms module generates court-ready PDF forms from tenant input
and document extraction data. Supports Minnesota eviction defense forms.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="court_forms",
        group_name="court_forms_list_types",
        title="Court Forms List Types (SSOT)",
        description=(
            "CANONICAL list of available court form types. Returns form codes, "
            "titles, and descriptions. Used by the form selection UI."
        ),
        inputs=(),
        outputs=("forms",),
        dependencies=("app.modules.court_forms.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="court_forms",
        group_name="court_forms_list_defenses",
        title="Court Forms List Defenses (SSOT)",
        description=(
            "CANONICAL list of available defense types for Answer forms. "
            "Returns defense codes, titles, and descriptions."
        ),
        inputs=(),
        outputs=("defenses",),
        dependencies=("app.modules.court_forms.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="court_forms",
        group_name="court_forms_generate",
        title="Court Forms Generate (SSOT)",
        description=(
            "CANONICAL generate a court form PDF from tenant input. Returns "
            "the generated PDF as base64 or a download URL."
        ),
        inputs=("form_type", "defenses?", "case_data", "user_id"),
        outputs=("form_id", "pdf", "filename"),
        dependencies=("app.modules.court_forms.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="court_forms",
        group_name="court_forms_generate_html",
        title="Court Forms Generate HTML (SSOT)",
        description=(
            "CANONICAL generate a court form as HTML for preview. Returns "
            "the form rendered as HTML for the tenant to review before "
            "generating the PDF."
        ),
        inputs=("form_type", "defenses?", "user_id"),
        outputs=("html",),
        dependencies=("app.modules.court_forms.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="court_forms",
        group_name="court_forms_download",
        title="Court Forms Download PDF (SSOT)",
        description=("CANONICAL download a generated court form as PDF. Returns the PDF file for download."),
        inputs=("form_type", "defenses?", "user_id"),
        outputs=("pdf", "filename"),
        dependencies=("app.modules.court_forms.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="court_forms",
        group_name="court_forms_preview",
        title="Court Forms Preview (SSOT)",
        description=(
            "CANONICAL preview a court form with data without generating "
            "the final PDF. Returns a preview for the tenant to review."
        ),
        inputs=("form_type", "defenses?", "case_data", "user_id"),
        outputs=("preview",),
        dependencies=("app.modules.court_forms.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="court_forms",
        group_name="court_forms_quick_answer",
        title="Court Forms Quick Answer (SSOT)",
        description=(
            "CANONICAL quick-generate an Answer form with minimal input. "
            "Used by the tenant dashboard's quick-action feature."
        ),
        inputs=("case_number?", "defendant_name?", "user_id"),
        outputs=("form_id", "pdf"),
        dependencies=("app.modules.court_forms.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="court_forms",
        group_name="court_forms_autofill",
        title="Court Forms Autofill From Documents (SSOT)",
        description=(
            "CANONICAL autofill a court form from uploaded documents. Extracts "
            "case number, parties, and facts from the tenant's documents to "
            "pre-populate the form."
        ),
        inputs=("form_type", "user_id"),
        outputs=("autofill_data",),
        dependencies=("app.modules.court_forms.router", "app.modules.documents.router"),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="court_forms",
        group_name="court_forms_generate_from_documents",
        title="Court Forms Generate From Documents (SSOT)",
        description=(
            "CANONICAL generate a complete court form from extracted document "
            "data. Combines autofill and generation in one step."
        ),
        inputs=("form_type", "defenses?", "user_id"),
        outputs=("form_id", "pdf"),
        dependencies=("app.modules.court_forms.router", "app.modules.documents.router"),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="court_forms",
        group_name="court_forms_document_data_preview",
        title="Court Forms Document Data Preview (SSOT)",
        description=(
            "CANONICAL preview the data extracted from documents that would "
            "be used to autofill a court form. Used by the form generation UI."
        ),
        inputs=("user_id",),
        outputs=("extracted_data",),
        dependencies=("app.modules.court_forms.router", "app.modules.documents.router"),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="court_forms",
        group_name="court_forms_library_list",
        title="Court Forms Library List (SSOT)",
        description=(
            "CANONICAL list of Minnesota civil and housing court forms from the "
            "JSON library. Returns form_id, title, category, case_type, and "
            "related forms."
        ),
        inputs=(),
        outputs=("forms",),
        dependencies=("app.modules.court_forms.router", "app.modules.court_forms.library"),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="court_forms",
        group_name="court_forms_library_get",
        title="Court Forms Library Get Definition (SSOT)",
        description=(
            "CANONICAL get a single form definition from the JSON library, "
            "including all required_fields and court_rules."
        ),
        inputs=("form_id",),
        outputs=("form_definition",),
        dependencies=("app.modules.court_forms.router", "app.modules.court_forms.library"),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="court_forms",
        group_name="court_forms_library_render",
        title="Court Forms Library Render (SSOT)",
        description=(
            "CANONICAL render a library form as HTML, text, or base64 PDF from "
            "confirmed field values."
        ),
        inputs=("form_id", "field_values", "output_format", "user_id"),
        outputs=("form_id", "title", "content", "fields_used", "missing_required"),
        dependencies=("app.modules.court_forms.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="court_forms",
        group_name="court_forms_library_save",
        title="Court Forms Library Save to Vault (SSOT)",
        description=(
            "CANONICAL generate a library form PDF and save it to the user's "
            "connected vault. Creates a FORM_FILL overlay attached to the "
            "generated PDF."
        ),
        inputs=("form_id", "field_values", "filename?", "user_id"),
        outputs=("form_id", "vault_id", "overlay_id", "storage_path", "filename"),
        dependencies=(
            "app.modules.court_forms.router",
            "app.services.vault_upload_service.VaultUploadService",
            "app.services.unified_overlay_manager.UnifiedOverlayManager",
            "app.core.overlay_types.OverlayType.FORM_FILL",
        ),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="court_forms",
        group_name="court_forms_library_packet",
        title="Court Forms Library Packet Assembly (SSOT)",
        description=(
            "CANONICAL render multiple library forms and merge them into a single "
            "PDF packet. Returns the packet as base64 PDF."
        ),
        inputs=("items", "filename"),
        outputs=("filename", "content", "form_ids"),
        dependencies=("app.modules.court_forms.router",),
        deterministic=False,
    )
)
