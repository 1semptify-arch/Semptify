"""Public Forms module registration helper — FunctionGroupContracts.

The public forms module handles public-facing form submissions:
feedback and contact forms. Also tenant autofill for public forms.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="public_forms",
        group_name="public_forms_feedback",
        title="Public Forms Submit Feedback (SSOT)",
        description="CANONICAL receive a feedback form submission from /public/feedback.html. Public endpoint.",
        inputs=("feedback",),
        outputs=("success",),
        dependencies=("app.modules.public_forms.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="public_forms",
        group_name="public_forms_tenant_autofill",
        title="Public Forms Tenant Autofill (SSOT)",
        description="CANONICAL autofill a public form for a tenant. Returns tenant data for form pre-population.",
        inputs=("request",),
        outputs=("autofill_data",),
        dependencies=("app.modules.public_forms.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="public_forms",
        group_name="public_forms_contact",
        title="Public Forms Submit Contact (SSOT)",
        description="CANONICAL receive a contact form submission. Public endpoint.",
        inputs=("contact",),
        outputs=("success",),
        dependencies=("app.modules.public_forms.router",),
        deterministic=False,
    )
)
