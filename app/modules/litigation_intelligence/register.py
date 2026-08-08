"""Litigation Intelligence module registration helper — FunctionGroupContracts.

The graph engine is implemented in app.modules.litigation_intelligence.graph_engine
and the router endpoints are live in product_manifest.py. Contracts are active.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="litigation_intelligence",
        group_name="litigation_intelligence_scrape_court",
        title="LIS Scrape Court System (SSOT)",
        description="CANONICAL scrape court system for case data.",
        inputs=("user_id", "request"),
        outputs=("results",),
        dependencies=("app.modules.litigation_intelligence.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="litigation_intelligence",
        group_name="litigation_intelligence_scrape_filings",
        title="LIS Scrape Case Filings (SSOT)",
        description="CANONICAL scrape specific case filings by case number.",
        inputs=("user_id", "case_number"),
        outputs=("filings",),
        dependencies=("app.modules.litigation_intelligence.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="litigation_intelligence",
        group_name="litigation_intelligence_normalize_entity",
        title="LIS Normalize Entity (SSOT)",
        description="CANONICAL normalize an entity name.",
        inputs=("user_id", "request"),
        outputs=("normalized",),
        dependencies=("app.modules.litigation_intelligence.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="litigation_intelligence",
        group_name="litigation_intelligence_normalize_entities",
        title="LIS Normalize Entities Batch (SSOT)",
        description="CANONICAL normalize multiple entity names at once.",
        inputs=("user_id", "request"),
        outputs=("normalized",),
        dependencies=("app.modules.litigation_intelligence.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="litigation_intelligence",
        group_name="litigation_intelligence_analyze_case",
        title="LIS Analyze Case Intelligence (SSOT)",
        description="CANONICAL analyze a case for intelligence patterns.",
        inputs=("user_id", "request"),
        outputs=("analysis",),
        dependencies=("app.modules.litigation_intelligence.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="litigation_intelligence",
        group_name="litigation_intelligence_get",
        title="LIS Get Case Intelligence (SSOT)",
        description="CANONICAL get stored intelligence report for a case.",
        inputs=("user_id", "case_id"),
        outputs=("intelligence",),
        dependencies=("app.modules.litigation_intelligence.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="litigation_intelligence",
        group_name="litigation_intelligence_graph_build",
        title="LIS Build Entity Graph (SSOT)",
        description="CANONICAL build entity relationship graph.",
        inputs=("user_id", "request"),
        outputs=("graph",),
        dependencies=("app.modules.litigation_intelligence.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="litigation_intelligence",
        group_name="litigation_intelligence_graph_visualize",
        title="LIS Generate Graph Visualization (SSOT)",
        description="CANONICAL generate graph visualization.",
        inputs=("user_id", "request"),
        outputs=("visualization",),
        dependencies=("app.modules.litigation_intelligence.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="litigation_intelligence",
        group_name="litigation_intelligence_graph_path",
        title="LIS Find Shortest Path (SSOT)",
        description="CANONICAL find shortest path between two entities in the graph.",
        inputs=("user_id", "source_entity", "target_entity"),
        outputs=("path",),
        dependencies=("app.modules.litigation_intelligence.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="litigation_intelligence",
        group_name="litigation_intelligence_report_generate",
        title="LIS Generate Report (SSOT)",
        description="CANONICAL generate litigation intelligence report.",
        inputs=("user_id", "request"),
        outputs=("report_id",),
        dependencies=("app.modules.litigation_intelligence.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="litigation_intelligence",
        group_name="litigation_intelligence_report_get",
        title="LIS Get Report (SSOT)",
        description="CANONICAL get a generated report by ID.",
        inputs=("user_id", "report_id"),
        outputs=("report",),
        dependencies=("app.modules.litigation_intelligence.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="litigation_intelligence",
        group_name="litigation_intelligence_report_export",
        title="LIS Export Report (SSOT)",
        description="CANONICAL export a generated report in specified format.",
        inputs=("user_id", "report_id", "format?"),
        outputs=("export",),
        dependencies=("app.modules.litigation_intelligence.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="litigation_intelligence",
        group_name="litigation_intelligence_task_schedule",
        title="LIS Schedule Task (SSOT)",
        description="CANONICAL schedule a new litigation intelligence task.",
        inputs=("user_id", "request"),
        outputs=("task_id",),
        dependencies=("app.modules.litigation_intelligence.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="litigation_intelligence",
        group_name="litigation_intelligence_tasks_list",
        title="LIS List Scheduled Tasks (SSOT)",
        description="CANONICAL get all scheduled tasks.",
        inputs=("user_id",),
        outputs=("tasks",),
        dependencies=("app.modules.litigation_intelligence.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="litigation_intelligence",
        group_name="litigation_intelligence_task_remove",
        title="LIS Remove Scheduled Task (SSOT)",
        description="CANONICAL remove a scheduled task by ID.",
        inputs=("user_id", "task_id"),
        outputs=("success",),
        dependencies=("app.modules.litigation_intelligence.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="litigation_intelligence",
        group_name="litigation_intelligence_statistics",
        title="LIS Statistics (SSOT)",
        description="CANONICAL get comprehensive litigation intelligence statistics.",
        inputs=("user_id",),
        outputs=("statistics",),
        dependencies=("app.modules.litigation_intelligence.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="litigation_intelligence",
        group_name="litigation_intelligence_health",
        title="LIS Health Check (SSOT)",
        description="CANONICAL health check for litigation intelligence system.",
        inputs=(),
        outputs=("status",),
        dependencies=("app.modules.litigation_intelligence.router",),
        deterministic=True,
    )
)
