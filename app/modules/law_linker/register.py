"""Law Linker module registration helper - FunctionGroupContracts.

The Law Linker marks legal citations on any text surface and opens an
official-source pop-out for Minnesota statutes and court rules.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="law_linker",
        group_name="law_linker_citation",
        title="Law Linker Citation (SSOT)",
        description=(
            "CANONICAL resolve a citation and return official source metadata plus "
            "fetched text. Used by the inline citation pop-out and law-linker.js."
        ),
        inputs=("citation",),
        outputs=("citation", "source_url", "text", "summary"),
        dependencies=("app.modules.law_linker.router",),
        deterministic=True,
        allowed_routes=("/api/law-linker/citation",),
        allowed_prefixes=("/api/law-linker",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="law_linker",
        group_name="law_linker_pop_out",
        title="Law Linker Pop-out (SSOT)",
        description=(
            "CANONICAL HTML pop-out page for a resolved citation. Renders "
            "pages/law_linker_popout.html with source metadata and a scratch-pad action."
        ),
        inputs=("citation",),
        outputs=("html",),
        dependencies=("app.modules.law_linker.router",),
        deterministic=True,
        allowed_routes=("/law-linker/pop-out",),
        allowed_prefixes=("/law-linker",),
    )
)
