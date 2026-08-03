"""Communication module registration helper — FunctionGroupContracts.

The communication module handles conversations and messages between users
(tenant ▸ advocate, tenant ▸ legal). It supports document collaboration
within conversations — reject, fill-and-sign, attachments.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="communication",
    group_name="communication_list_conversations",
    title="Communication List Conversations (SSOT)",
    description=(
        "CANONICAL list of conversations for the current user. Returns "
        "conversation summaries with last message, unread count, and "
        "participant info."
    ),
    inputs=("user_id", "access_token"),
    outputs=("conversations",),
    dependencies=("app.modules.communication.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="communication",
    group_name="communication_create_conversation",
    title="Communication Create Conversation (SSOT)",
    description=(
        "CANONICAL create a new conversation. The user specifies the "
        "recipient and initial message. Returns the new conversation."
    ),
    inputs=("user_id", "recipient", "initial_message", "access_token"),
    outputs=("conversation_id", "conversation"),
    dependencies=("app.modules.communication.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="communication",
    group_name="communication_get_conversation",
    title="Communication Get Conversation (SSOT)",
    description=(
        "CANONICAL get a single conversation with message thread. Supports "
        "pagination via before_message_id. Returns messages in chronological "
        "order."
    ),
    inputs=("conversation_id", "before_message_id?", "access_token"),
    outputs=("messages", "has_more"),
    dependencies=("app.modules.communication.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="communication",
    group_name="communication_send_message",
    title="Communication Send Message (SSOT)",
    description=(
        "CANONICAL send a message in a conversation. Returns the new "
        "message with ID and timestamp."
    ),
    inputs=("conversation_id", "content", "access_token"),
    outputs=("message_id", "sent_at"),
    dependencies=("app.modules.communication.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="communication",
    group_name="communication_mark_message_read",
    title="Communication Mark Message Read (SSOT)",
    description=(
        "CANONICAL mark a single message as read. Updates the read "
        "receipt for the message."
    ),
    inputs=("conversation_id", "message_id", "access_token"),
    outputs=("success",),
    dependencies=("app.modules.communication.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="communication",
    group_name="communication_mark_conversation_read",
    title="Communication Mark Conversation Read (SSOT)",
    description=(
        "CANONICAL mark all messages in a conversation as read. "
        "Updates the unread count to zero."
    ),
    inputs=("conversation_id", "access_token"),
    outputs=("success",),
    dependencies=("app.modules.communication.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="communication",
    group_name="communication_reject_document",
    title="Communication Reject Document (SSOT)",
    description=(
        "CANONICAL reject a document delivered through the communication "
        "channel. The recipient provides a reason for rejection."
    ),
    inputs=("delivery_id", "reason", "access_token"),
    outputs=("status",),
    dependencies=("app.modules.communication.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="communication",
    group_name="communication_fill_and_sign",
    title="Communication Fill and Sign Document (SSOT)",
    description=(
        "CANONICAL fill and sign a document delivered through the "
        "communication channel. Supports typed, drawn, and digital "
        "signatures."
    ),
    inputs=("delivery_id", "signature_type", "access_token"),
    outputs=("signed_document",),
    dependencies=("app.modules.communication.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="communication",
    group_name="communication_upload_attachment",
    title="Communication Upload Attachment (SSOT)",
    description=(
        "CANONICAL upload a file attachment to a conversation. The file "
        "is stored in the sender's vault and linked to the conversation."
    ),
    inputs=("conversation_id", "file", "access_token"),
    outputs=("attachment_id", "filename"),
    dependencies=("app.modules.communication.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="communication",
    group_name="communication_delivery_conversation",
    title="Communication Delivery Conversation (SSOT)",
    description=(
        "CANONICAL get the conversation associated with a document delivery. "
        "Returns the conversation thread for the delivery."
    ),
    inputs=("delivery_id", "access_token"),
    outputs=("conversation",),
    dependencies=("app.modules.communication.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="communication",
    group_name="communication_typing_indicator",
    title="Communication Typing Indicator (SSOT)",
    description=(
        "CANONICAL send a typing indicator for a conversation. Notifies "
        "the other participant that the user is typing."
    ),
    inputs=("conversation_id", "is_typing"),
    outputs=("success",),
    dependencies=("app.modules.communication.router",),
    deterministic=False,
))
