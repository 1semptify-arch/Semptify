"""Public surface module contract."""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="public_surface",
        group_name="landing_and_i18n",
        title="Public Landing & i18n (SSOT)",
        description=(
            "Public, stateless endpoints for the landing page and locale. "
            "GET /api/landing/facts returns verified, non-expired public facts. "
            "GET /api/i18n/locale and POST /api/i18n/set-locale expose/change "
            "the user's locale preference. No storage session required."
        ),
        inputs=("locale?",),
        outputs=("facts", "locale"),
        dependencies=("app.modules.public_surface.router", "app.core.i18n"),
        deterministic=True,
        tier="T0",
        allowed_routes=(
            "/api/landing/facts",
            "/api/i18n/locale",
            "/api/i18n/set-locale",
        ),
        allowed_prefixes=("/api/landing", "/api/i18n"),
    )
)
