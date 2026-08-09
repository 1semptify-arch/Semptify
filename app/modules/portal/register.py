"""Portal module registration helper."""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="portal",
        group_name="portal_services",
        title="Portal Services (SSOT)",
        description=(
            "CANONICAL list of services on the semptify.org guest portal. "
            "Returns the public services catalog grouped by category. "
            "Each service is a self-contained entry (name, description, CTA, path). "
            "New services are added to the registry — no rewriting the portal page. "
            "Does NOT handle onboarding; use the module onboarding system for that."
        ),
        inputs=("category?", "service_id?"),
        outputs=("services", "categories"),
        dependencies=("app.modules.portal.registry",),
        deterministic=True,
    )
)
