"""Court Packet module registration helper — FunctionGroupContracts.

The court packet module assembles a complete court-ready packet from the
tenant's documents, evidence, timeline, and legal documents.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(FunctionGroupContract(
    module="court_packet",
    group_name="court_packet_status",
    title="Court Packet Status (SSOT)",
    description="CANONICAL get current court packet status and contents summary. Returns what's included and what's missing.",
    inputs=("user_id",),
    outputs=("status", "contents"),
    dependencies=("app.modules.court_packet.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="court_packet",
    group_name="court_packet_documents",
    title="Court Packet Documents (SSOT)",
    description="CANONICAL get all documents available for the court packet. Returns categorized documents.",
    inputs=("user_id",),
    outputs=("documents",),
    dependencies=("app.modules.court_packet.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="court_packet",
    group_name="court_packet_evidence",
    title="Court Packet Evidence (SSOT)",
    description="CANONICAL get all evidence documents for the court packet. Returns evidence categorized by type.",
    inputs=("user_id",),
    outputs=("evidence",),
    dependencies=("app.modules.court_packet.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="court_packet",
    group_name="court_packet_legal_documents",
    title="Court Packet Legal Documents (SSOT)",
    description="CANONICAL get all legal documents for the court packet (notices, filings, etc.).",
    inputs=("user_id",),
    outputs=("legal_documents",),
    dependencies=("app.modules.court_packet.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="court_packet",
    group_name="court_packet_timeline",
    title="Court Packet Timeline (SSOT)",
    description="CANONICAL get aggregated timeline events from all processed documents for the court packet.",
    inputs=("user_id",),
    outputs=("timeline",),
    dependencies=("app.modules.court_packet.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="court_packet",
    group_name="court_packet_checklist",
    title="Court Packet Checklist (SSOT)",
    description="CANONICAL get checklist of recommended items for the court packet. Returns what's included and what's missing.",
    inputs=("user_id",),
    outputs=("checklist",),
    dependencies=("app.modules.court_packet.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="court_packet",
    group_name="court_packet_generate",
    title="Court Packet Generate (SSOT)",
    description="CANONICAL generate the complete court packet. Returns the generated packet as a PDF or zip.",
    inputs=("user_id", "include_highlights?"),
    outputs=("packet", "filename"),
    dependencies=("app.modules.court_packet.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="court_packet",
    group_name="court_packet_preview",
    title="Court Packet Preview (SSOT)",
    description="CANONICAL preview what would be included in the court packet. Returns a preview without generating the final packet.",
    inputs=("user_id",),
    outputs=("preview",),
    dependencies=("app.modules.court_packet.router",),
    deterministic=True,
))
