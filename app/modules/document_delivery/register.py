"""Document Delivery module registration helper — FunctionGroupContracts.

The document delivery module handles sending documents from professionals
(advocates, managers, legal) to tenants. Includes inbox, outbox, read
receipts, signing, and rejection.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(FunctionGroupContract(
    module="document_delivery",
    group_name="document_delivery_health",
    title="Document Delivery Health (SSOT)",
    description="CANONICAL health check endpoint for the document delivery module.",
    inputs=(),
    outputs=("status",),
    dependencies=("app.modules.document_delivery.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="document_delivery",
    group_name="document_delivery_inbox_page",
    title="Document Delivery Inbox Page (SSOT)",
    description="CANONICAL serve the tenant document delivery inbox page. Returns HTML.",
    inputs=("request",),
    outputs=("html",),
    dependencies=("app.modules.document_delivery.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="document_delivery",
    group_name="document_delivery_send",
    title="Document Delivery Send (SSOT)",
    description="CANONICAL send a document from a professional to a tenant. Creates a delivery record.",
    inputs=("recipient_id", "document_id", "access_token"),
    outputs=("delivery_id",),
    dependencies=("app.modules.document_delivery.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="document_delivery",
    group_name="document_delivery_inbox",
    title="Document Delivery Inbox (SSOT)",
    description="CANONICAL get the tenant's delivery inbox. Returns all deliveries sent to the tenant.",
    inputs=("user_id", "access_token"),
    outputs=("deliveries",),
    dependencies=("app.modules.document_delivery.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="document_delivery",
    group_name="document_delivery_outbox",
    title="Document Delivery Outbox (SSOT)",
    description="CANONICAL get the professional's delivery outbox. Returns all deliveries sent by the professional.",
    inputs=("user_id", "access_token"),
    outputs=("deliveries",),
    dependencies=("app.modules.document_delivery.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="document_delivery",
    group_name="document_delivery_get",
    title="Document Delivery Get (SSOT)",
    description="CANONICAL get a specific delivery by ID. Returns full delivery details including document.",
    inputs=("delivery_id", "access_token"),
    outputs=("delivery",),
    dependencies=("app.modules.document_delivery.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="document_delivery",
    group_name="document_delivery_mark_viewed",
    title="Document Delivery Mark Viewed (SSOT)",
    description="CANONICAL mark a delivery as viewed. Updates the read receipt for the delivery.",
    inputs=("delivery_id", "access_token"),
    outputs=("success",),
    dependencies=("app.modules.document_delivery.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="document_delivery",
    group_name="document_delivery_sign",
    title="Document Delivery Sign (SSOT)",
    description="CANONICAL sign a delivered document. Tenant applies a signature to the document.",
    inputs=("delivery_id", "signature_type", "access_token"),
    outputs=("signed_document",),
    dependencies=("app.modules.document_delivery.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="document_delivery",
    group_name="document_delivery_reject",
    title="Document Delivery Reject (SSOT)",
    description="CANONICAL reject a delivered document. Tenant provides a reason for rejection.",
    inputs=("delivery_id", "reason", "access_token"),
    outputs=("success",),
    dependencies=("app.modules.document_delivery.router",),
    deterministic=False,
))
