"""Law Library module registration helper — FunctionGroupContracts.

The law library is the KNOW pillar's reference layer. It provides the full
catalog of statutes, court rules, case law, and legal references. Tenants use
it to look up specific laws; the Context Engine uses it to cite sources.
Facts only — no interpretations, no opinions, no legal advice.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="law_library",
        group_name="law_library_list_statutes",
        title="Law Library List Statutes (SSOT)",
        description=(
            "CANONICAL list of statutes in the law library. Supports filtering by "
            "category and full-text search in title and summary. Returns statute "
            "summaries with citation and category."
        ),
        inputs=("category?", "search?"),
        outputs=("statutes", "total"),
        dependencies=("app.modules.law_library.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="law_library",
        group_name="law_library_get_statute",
        title="Law Library Get Statute (SSOT)",
        description=(
            "CANONICAL detailed view of a single statute. Returns full text, "
            "citation, category, and related cases. Used by the statute detail view."
        ),
        inputs=("statute_id",),
        outputs=("statute",),
        dependencies=("app.modules.law_library.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="law_library",
        group_name="law_library_list_court_rules",
        title="Law Library List Court Rules (SSOT)",
        description=(
            "CANONICAL list of court rules. Supports filtering by category. "
            "Returns rule summaries with citation and jurisdiction."
        ),
        inputs=("category?",),
        outputs=("court_rules", "total"),
        dependencies=("app.modules.law_library.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="law_library",
        group_name="law_library_get_court_rule",
        title="Law Library Get Court Rule (SSOT)",
        description=(
            "CANONICAL detailed view of a single court rule. Returns full text, citation, and related procedures."
        ),
        inputs=("rule_id",),
        outputs=("court_rule",),
        dependencies=("app.modules.law_library.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="law_library",
        group_name="law_library_list_case_law",
        title="Law Library List Case Law (SSOT)",
        description=(
            "CANONICAL list of case law precedents. Supports full-text search in "
            "case name and summary. Returns case summaries with citation and holding."
        ),
        inputs=("search?"),
        outputs=("cases", "total"),
        dependencies=("app.modules.law_library.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="law_library",
        group_name="law_library_get_case",
        title="Law Library Get Case (SSOT)",
        description=(
            "CANONICAL detailed view of a single case. Returns full case text, citation, holding, and related statutes."
        ),
        inputs=("case_id",),
        outputs=("case",),
        dependencies=("app.modules.law_library.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="law_library",
        group_name="law_library_links",
        title="Law Library Card Link Index (SSOT)",
        description=(
            "CANONICAL index of every law, case, and court rule with its URL. "
            "Used by the tenant UI to render quick-link cards. Returns a flat list "
            "of all references with their type and title."
        ),
        inputs=(),
        outputs=("links",),
        dependencies=("app.modules.law_library.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="law_library",
        group_name="law_library_categories",
        title="Law Library Categories (SSOT)",
        description=(
            "CANONICAL list of all categories in the law library. Used by the tenant UI to render category navigation."
        ),
        inputs=(),
        outputs=("categories",),
        dependencies=("app.modules.law_library.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="law_library",
        group_name="law_library_quick_reference",
        title="Law Library Quick Reference (SSOT)",
        description=(
            "CANONICAL quick reference for a specific topic. Returns a summary "
            "of key laws, rules, and cases for the topic. Used by the tenant UI's "
            "quick-reference cards."
        ),
        inputs=("topic",),
        outputs=("summary", "key_laws", "key_cases"),
        dependencies=("app.modules.law_library.router",),
        deterministic=True,
    )
)
