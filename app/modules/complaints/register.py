"""Complaints module registration helper — FunctionGroupContracts.

The complaints module is the KNOW pillar's agency layer. It helps tenants
file complaints with housing agencies by providing agency info, checklists,
draft generation, and a wizard. Facts only — the tenant files themselves.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="complaints",
        group_name="complaints_list_agencies",
        title="Complaints List Agencies (SSOT)",
        description=(
            "CANONICAL list of housing agencies. Supports filtering by agency type. "
            "Returns agency names, types, jurisdictions, and contact info."
        ),
        inputs=("agency_type?"),
        outputs=("agencies", "total"),
        dependencies=("app.modules.complaints.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="complaints",
        group_name="complaints_get_agency",
        title="Complaints Get Agency (SSOT)",
        description=(
            "CANONICAL details for a specific agency. Returns full agency info "
            "including filing methods, contact info, and jurisdiction."
        ),
        inputs=("agency_id",),
        outputs=("agency",),
        dependencies=("app.modules.complaints.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="complaints",
        group_name="complaints_recommend_agencies",
        title="Complaints Recommend Agencies (SSOT)",
        description=(
            "CANONICAL agency recommendations based on the tenant's situation. "
            "Takes keywords describing the situation and returns agencies that "
            "handle those issues. Facts only — not a recommendation to file."
        ),
        inputs=("keywords", "jurisdiction?"),
        outputs=("agencies",),
        dependencies=("app.modules.complaints.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="complaints",
        group_name="complaints_agency_checklist",
        title="Complaints Agency Checklist (SSOT)",
        description=(
            "CANONICAL filing checklist for a specific agency. Returns the list "
            "of required documents, forms, and steps for filing with that agency."
        ),
        inputs=("agency_id",),
        outputs=("checklist",),
        dependencies=("app.modules.complaints.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="complaints",
        group_name="complaints_create_draft",
        title="Complaints Create Draft (SSOT)",
        description=(
            "CANONICAL create a complaint draft. The tenant provides their "
            "situation details, and the system generates a formatted draft. "
            "The tenant reviews and edits before filing."
        ),
        inputs=("user_id", "agency_id", "situation"),
        outputs=("draft_id", "draft"),
        dependencies=("app.modules.complaints.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="complaints",
        group_name="complaints_list_drafts",
        title="Complaints List Drafts (SSOT)",
        description=(
            "CANONICAL list of complaint drafts for a user. Returns all drafts with status (draft, filed, archived)."
        ),
        inputs=("user_id",),
        outputs=("drafts",),
        dependencies=("app.modules.complaints.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="complaints",
        group_name="complaints_get_draft",
        title="Complaints Get Draft (SSOT)",
        description=("CANONICAL retrieval of a specific complaint draft. Returns the full draft text and metadata."),
        inputs=("draft_id",),
        outputs=("draft",),
        dependencies=("app.modules.complaints.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="complaints",
        group_name="complaints_update_draft",
        title="Complaints Update Draft (SSOT)",
        description=(
            "CANONICAL update of a complaint draft. The tenant can edit the "
            "draft text, add details, or attach documents."
        ),
        inputs=("draft_id", "updates"),
        outputs=("draft",),
        dependencies=("app.modules.complaints.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="complaints",
        group_name="complaints_delete_draft",
        title="Complaints Delete Draft (SSOT)",
        description=("CANONICAL deletion of a complaint draft. Removes the draft and all associated data."),
        inputs=("draft_id",),
        outputs=("status",),
        dependencies=("app.modules.complaints.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="complaints",
        group_name="complaints_preview",
        title="Complaints Preview (SSOT)",
        description=(
            "CANONICAL preview of a complaint draft as it would appear when filed. "
            "Returns formatted HTML or text for review."
        ),
        inputs=("draft_id",),
        outputs=("preview", "format"),
        dependencies=("app.modules.complaints.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="complaints",
        group_name="complaints_export",
        title="Complaints Export (SSOT)",
        description=(
            "CANONICAL export of a complaint draft in a specific format "
            "(text, html, pdf). The tenant downloads and files it themselves."
        ),
        inputs=("draft_id", "format?"),
        outputs=("file_stream", "filename", "format"),
        dependencies=("app.modules.complaints.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="complaints",
        group_name="complaints_mark_filed",
        title="Complaints Mark Filed (SSOT)",
        description=(
            "CANONICAL mark a complaint draft as filed. The tenant indicates they "
            "have filed the complaint with the agency. Updates the draft status "
            "and records the filing date."
        ),
        inputs=("draft_id", "filed_date"),
        outputs=("draft_id", "status", "filed_date"),
        dependencies=("app.modules.complaints.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="complaints",
        group_name="complaints_quick_start",
        title="Complaints Quick Start Guide (SSOT)",
        description=(
            "CANONICAL quick start guide for filing complaints. Returns the "
            "basic steps and first agencies to consider. Used by the tenant UI's "
            "complaints getting-started card."
        ),
        inputs=(),
        outputs=("steps", "agencies"),
        dependencies=("app.modules.complaints.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="complaints",
        group_name="complaints_wizard_start",
        title="Complaints Wizard Start (SSOT)",
        description=(
            "CANONICAL start a new complaint wizard session. The wizard walks "
            "the tenant through the complaint filing process step by step."
        ),
        inputs=("user_id",),
        outputs=("session_id", "first_step"),
        dependencies=("app.modules.complaints.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="complaints",
        group_name="complaints_wizard_get",
        title="Complaints Wizard Get Session (SSOT)",
        description=(
            "CANONICAL get the current state of a complaint wizard session. "
            "Returns the current step, completed steps, and remaining steps."
        ),
        inputs=("session_id",),
        outputs=("session", "current_step"),
        dependencies=("app.modules.complaints.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="complaints",
        group_name="complaints_submit",
        title="Complaints Submit (SSOT)",
        description=(
            "CANONICAL submit a completed complaint. Finalizes the wizard session, "
            "creates a draft, and marks it ready for the tenant to file. "
            "Does NOT file on the tenant's behalf."
        ),
        inputs=("session_id", "user_id"),
        outputs=("draft_id", "status"),
        dependencies=("app.modules.complaints.router",),
        deterministic=False,
    )
)
