"""Court Forms module registration helper — FunctionGroupContracts.

The court forms module generates court-ready PDF forms from tenant input
and document extraction data. Supports Minnesota eviction defense forms.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(FunctionGroupContract(
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
))

register_function_group(FunctionGroupContract(
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
))

register_function_group(FunctionGroupContract(
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
))

register_function_group(FunctionGroupContract(
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
))

register_function_group(FunctionGroupContract(
    module="court_forms",
    group_name="court_forms_download",
    title="Court Forms Download PDF (SSOT)",
    description=(
        "CANONICAL download a generated court form as PDF. Returns the "
        "PDF file for download."
    ),
    inputs=("form_type", "defenses?", "user_id"),
    outputs=("pdf", "filename"),
    dependencies=("app.modules.court_forms.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
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
))

register_function_group(FunctionGroupContract(
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
))

register_function_group(FunctionGroupContract(
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
))

register_function_group(FunctionGroupContract(
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
))

register_function_group(FunctionGroupContract(
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
))
